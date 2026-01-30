import os
import time
import random
import datetime
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
THREADS = 2           
BURST_SIZE = 8        
BURST_DELAY = 0.15    
CYCLE_DELAY = 1.2     
SESSION_DURATION = 1200 
REFRESH_INTERVAL = 300 
LOG_FILE = "message_log.txt"

# GLOBAL COUNTER
GLOBAL_SENT = 0
COUNTER_LOCK = threading.Lock()

def write_log(msg):
    """Writes to file immediately to prevent 'No File Found' errors"""
    try:
        with open(LOG_FILE, "a") as f: 
            f.write(msg + "\n")
    except: pass

def log_status(agent_id, msg):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] 🤖 Agent {agent_id}: {msg}"
    print(entry, flush=True)
    write_log(entry)

def log_speed(agent_id, current_sent, start_time):
    elapsed = time.time() - start_time
    if elapsed == 0: elapsed = 1
    speed = current_sent / elapsed
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    with COUNTER_LOCK:
        total = GLOBAL_SENT
        
    entry = f"[{timestamp}] ⚡ Agent {agent_id} | Session Total: {total} | Speed: {speed:.1f} msg/s"
    print(entry, flush=True)
    write_log(entry)

def get_driver(agent_id):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    
    chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/12{agent_id+2}.0.0.0 Safari/537.36")
    chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_p_{agent_id}_{random.randint(1,99999)}")
    
    return webdriver.Chrome(options=chrome_options)

def perform_login(driver, agent_id, username, password):
    log_status(agent_id, f"⚠️ Session Expired. Attempting Auto-Login for {username}...")
    try:
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(6)
        try: driver.find_element(By.XPATH, "//button[contains(text(), 'Allow')]").click()
        except: pass

        user_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))
        user_input.send_keys(username)
        pass_input = driver.find_element(By.NAME, "password")
        pass_input.send_keys(password)
        time.sleep(1)
        pass_input.send_keys(Keys.ENTER)
        
        log_status(agent_id, "🔐 Login submitted. Waiting 12s...")
        time.sleep(12)
        
        if "login" not in driver.current_url:
            log_status(agent_id, "✅ Auto-Login Successful!")
            return True
        else:
            log_status(agent_id, "❌ Login Failed.")
            return False
    except Exception as e:
        log_status(agent_id, f"❌ Login Error: {e}")
        return False

def instant_inject(driver, element, text):
    driver.execute_script("""
        var elm = arguments[0], txt = arguments[1];
        elm.focus();
        document.execCommand('insertText', false, txt);
        elm.dispatchEvent(new Event('input', {bubbles: true}));
    """, element, text)

def run_life_cycle(agent_id, user, pw, cookie, target, messages):
    driver = None
    sent_in_this_life = 0
    session_start_time = time.time()
    last_refresh_time = time.time()
    
    try:
        log_status(agent_id, "🚀 Phoenix Rising...")
        driver = get_driver(agent_id)
        
        driver.get("https://www.instagram.com/404") 
        if cookie:
            clean_session = cookie.split("sessionid=")[1].split(";")[0] if "sessionid=" in cookie else cookie
            driver.add_cookie({'name': 'sessionid', 'value': clean_session, 'domain': '.instagram.com', 'path': '/'})
        
        driver.refresh()
        time.sleep(5)

        driver.get(f"https://www.instagram.com/direct/t/{target}/")
        time.sleep(5)
        
        if "login" in driver.current_url:
            if not perform_login(driver, agent_id, user, pw):
                return
            driver.get(f"https://www.instagram.com/direct/t/{target}/")
            time.sleep(5)

        box_xpath = "//div[@contenteditable='true']"
        msg_box = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, box_xpath)))

        while (time.time() - session_start_time) < SESSION_DURATION:
            if (time.time() - last_refresh_time) > REFRESH_INTERVAL:
                log_status(agent_id, "♻️ RAM Soft Refresh...")
                driver.refresh()
                time.sleep(5)
                msg_box = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, box_xpath)))
                last_refresh_time = time.time()

            try:
                for _ in range(BURST_SIZE):
                    msg = random.choice(messages)
                    jitter = "⠀" * random.randint(0, 1)
                    instant_inject(driver, msg_box, f"{msg}{jitter}")
                    msg_box.send_keys(Keys.ENTER)
                    sent_in_this_life += 1
                    with COUNTER_LOCK:
                        global GLOBAL_SENT
                        GLOBAL_SENT += 1
                    time.sleep(random.uniform(0.12, 0.20))
                
                log_speed(agent_id, sent_in_this_life, session_start_time)
                time.sleep(CYCLE_DELAY)
            except Exception:
                break 

    except Exception as e:
        log_status(agent_id, f"Error: {e}")
    finally:
        if driver:
            try: driver.quit()
            except: pass
        try: shutil.rmtree(f"/tmp/chrome_p_{agent_id}", ignore_errors=True)
        except: pass

def agent_worker(agent_id, user, pw, cookie, target, messages):
    while True:
        run_life_cycle(agent_id, user, pw, cookie, target, messages)
        time.sleep(5)

def main():
    # 🚨 CRITICAL FIX: Create file immediately on start
    with open(LOG_FILE, "w") as f:
        f.write(f"--- SESSION START: {datetime.datetime.now()} ---\n")
    
    print(f"🔥 V22.2 LOG FIX | {THREADS} THREADS", flush=True)
    
    user = os.environ.get("INSTA_USER", "").strip()
    pw = os.environ.get("INSTA_PASS", "").strip()
    cookie = os.environ.get("INSTA_COOKIE", "").strip()
    target = os.environ.get("TARGET_THREAD_ID", "").strip()
    messages = os.environ.get("MESSAGES", "Hello").split("|")

    # Log specific errors to file if vars are missing
    if not user or not pw: 
        err = "❌ CRITICAL ERROR: INSTA_USER or INSTA_PASS is missing from Secrets!"
        print(err)
        write_log(err)
        return

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            executor.submit(agent_worker, i+1, user, pw, cookie, target, messages)

if __name__ == "__main__":
    main()
