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
from selenium.webdriver.common.action_chains import ActionChains

# --- CONFIGURATION ---
THREADS = 2           
BURST_SIZE = 5        
BURST_DELAY = 1.5     # Slower to allow Paste operation
CYCLE_DELAY = 2.0     
SESSION_DURATION = 1200 
REFRESH_INTERVAL = 300 
LOG_FILE = "message_log.txt"

GLOBAL_SENT = 0
COUNTER_LOCK = threading.Lock()

def write_log(msg):
    try:
        with open(LOG_FILE, "a") as f: f.write(msg + "\n")
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
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Enable Clipboard Permissions
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/12{agent_id+2}.0.0.0 Safari/537.36")
    chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_p_{agent_id}_{random.randint(1,99999)}")
    return webdriver.Chrome(options=chrome_options)

def perform_login(driver, agent_id, username, password):
    log_status(agent_id, f"⚠️ Session Expired. Auto-Login for {username}...")
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
        
        log_status(agent_id, "🔐 Credentials sent...")
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

def find_chat_box(driver):
    selectors = [
        "//div[@contenteditable='true']",
        "//div[@role='textbox']",
        "//textarea"
    ]
    for xpath in selectors:
        try: return driver.find_element(By.XPATH, xpath)
        except: continue
    return None

def clipboard_paste_send(driver, element, text):
    """
    V29: CLIPBOARD BYPASS
    1. Sets the value of the clipboard using JS (Headless compatible)
    2. Focuses the chat box
    3. Simulates CTRL+V (Paste)
    4. Simulates ENTER
    """
    
    # 1. Clear previous text just in case
    # element.clear() # Sometimes this breaks React, so we skip it or use keys
    
    # 2. Focus
    element.click()
    
    # 3. Type the text "Human Style" (Char by Char)
    # Since CTRL+V is hard in headless Linux sometimes, falling back 
    # to character typing with ActionChains is more reliable than 'injecting'.
    
    actions = ActionChains(driver)
    actions.move_to_element(element)
    actions.click()
    
    # Type letter by letter (This guarantees the event fires)
    for char in text:
        actions.send_keys(char)
        
    # Send Enter
    actions.send_keys(Keys.ENTER)
    actions.perform()

def run_life_cycle(agent_id, user, pw, cookie, target, messages):
    driver = None
    sent_in_this_life = 0
    session_start_time = time.time()
    last_refresh_time = time.time()
    
    try:
        log_status(agent_id, "🚀 Phoenix Rising...")
        driver = get_driver(agent_id)
        
        driver.get("https://www.instagram.com/")
        time.sleep(3)
        if "instagram.com" not in driver.current_url:
            driver.get("https://www.instagram.com/")
            time.sleep(5)

        if cookie:
            clean_session = cookie.split("sessionid=")[1].split(";")[0] if "sessionid=" in cookie else cookie
            driver.add_cookie({'name': 'sessionid', 'value': clean_session, 'path': '/'})
            
        driver.refresh()
        time.sleep(5)

        target_url = f"https://www.instagram.com/direct/t/{target}/"
        log_status(agent_id, f"🔍 Navigating to: .../direct/t/{target[:5]}...")
        driver.get(target_url)
        time.sleep(5)
        
        # Clear Popups
        try: driver.find_element(By.XPATH, "//button[text()='Not Now']").click()
        except: pass

        if "login" in driver.current_url:
            if not perform_login(driver, agent_id, user, pw):
                return
            driver.get(target_url)
            time.sleep(5)

        msg_box = find_chat_box(driver)
        if not msg_box:
            log_status(agent_id, f"❌ ERROR: Chat box not found.")
            if "/inbox" in driver.current_url and "/t/" not in driver.current_url:
                log_status(agent_id, "💀 FATAL: Redirected to Inbox. ID Invalid.")
            return

        log_status(agent_id, "✅ Target Locked. Sending...")

        while (time.time() - session_start_time) < SESSION_DURATION:
            if (time.time() - last_refresh_time) > REFRESH_INTERVAL:
                log_status(agent_id, "♻️ RAM Soft Refresh...")
                driver.refresh()
                time.sleep(5)
                msg_box = find_chat_box(driver)
                if not msg_box: break
                last_refresh_time = time.time()

            try:
                for _ in range(BURST_SIZE):
                    msg = random.choice(messages)
                    jitter = "⠀" * random.randint(0, 1)
                    
                    # 🚨 V29: USE ACTION CHAINS (Mimics Keyboard Hardware)
                    clipboard_paste_send(driver, msg_box, f"{msg}{jitter}")

                    sent_in_this_life += 1
                    with COUNTER_LOCK:
                        global GLOBAL_SENT
                        GLOBAL_SENT += 1
                    time.sleep(random.uniform(0.15, 0.25))
                
                log_speed(agent_id, sent_in_this_life, session_start_time)
                time.sleep(CYCLE_DELAY)
            except Exception as e:
                log_status(agent_id, f"⚠️ Loop Error: {e}")
                msg_box = find_chat_box(driver)
                if not msg_box: break

    except Exception as e:
        log_status(agent_id, f"❌ Critical Crash: {e}")
    finally:
        if driver:
            try: driver.quit()
            except: pass
        try: shutil.rmtree(f"/tmp/chrome_p_{agent_id}", ignore_errors=True)
        except: pass

def agent_worker(agent_id, user, pw, cookie, target, messages):
    while True:
        run_life_cycle(agent_id, user, pw, cookie, target, messages)
        time.sleep(10)

def main():
    with open(LOG_FILE, "w") as f:
        f.write(f"--- SESSION START: {datetime.datetime.now()} ---\n")
    
    print(f"🔥 V29 KEYBOARD MIMIC | {THREADS} THREADS", flush=True)
    
    user = os.environ.get("INSTA_USER", "").strip()
    pw = os.environ.get("INSTA_PASS", "").strip()
    cookie = os.environ.get("INSTA_COOKIE", "").strip()
    target = os.environ.get("TARGET_THREAD_ID", "").strip()
    messages = os.environ.get("MESSAGES", "Hello").split("|")

    if not user or not pw: 
        print("❌ CRITICAL: Secrets Missing!")
        return

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            executor.submit(agent_worker, i+1, user, pw, cookie, target, messages)

if __name__ == "__main__":
    main()
