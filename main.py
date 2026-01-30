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
BURST_SIZE = 5        
BURST_DELAY = 1.0     
CYCLE_DELAY = 3.0     
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
    
    # MANUAL MOBILE METRICS (Pixel 5)
    mobile_emulation = {
        "deviceMetrics": { "width": 393, "height": 851, "pixelRatio": 3.0 },
        "userAgent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_p_{agent_id}_{random.randint(1,99999)}")
    return webdriver.Chrome(options=chrome_options)

def clear_popups(driver, agent_id):
    """
    V34: UI BULLDOZER
    Aggressively clicks every known 'Close' button to reveal the chat.
    """
    buttons_to_click = [
        "//button[text()='Not Now']",
        "//button[text()='Cancel']",
        "//div[text()='Not now']",
        "//button[contains(text(), 'Use the App')]/following-sibling::button", # Close app upsell
        "//div[@role='dialog']//button[contains(@aria-label, 'Close')]"
    ]
    
    for xpath in buttons_to_click:
        try:
            btn = driver.find_element(By.XPATH, xpath)
            btn.click()
            log_status(agent_id, f"🧹 Cleared Popup: {xpath}")
            time.sleep(1)
        except:
            pass
            
    # Blind Escape Key (Closes generic modals)
    try: ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    except: pass

def full_login_flow(driver, agent_id, username, password):
    log_status(agent_id, f"🔑 Starting Fresh Login for {username}...")
    try:
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(5)
        
        try: driver.find_element(By.XPATH, "//button[contains(text(), 'Allow')]").click()
        except: pass

        user_input = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "username")))
        user_input.send_keys(username)
        time.sleep(1)
        
        pass_input = driver.find_element(By.NAME, "password")
        pass_input.send_keys(password)
        time.sleep(1)
        
        try:
            login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_btn.click()
        except:
            pass_input.send_keys(Keys.ENTER)
            
        log_status(agent_id, "⏳ Verifying Credentials...")
        time.sleep(10)
        
        # Handle Post-Login Popups
        clear_popups(driver, agent_id)

        driver.get("https://www.instagram.com/")
        time.sleep(5)
        
        if "login" in driver.current_url:
            log_status(agent_id, "❌ Fresh Login Failed.")
            driver.save_screenshot(f"debug_login_fail_{agent_id}.png")
            return False
            
        log_status(agent_id, "✅ Fresh Login Successful!")
        return True

    except Exception as e:
        log_status(agent_id, f"❌ Login Crash: {e}")
        return False

def find_mobile_box(driver):
    """
    V34: EXPANDED SELECTORS
    Tries 5 different ways to find the chat box on Mobile Web.
    """
    selectors = [
        "//textarea", 
        "//div[@role='textbox']",
        "//textarea[contains(@placeholder, 'Message...')]",
        "//div[contains(@aria-label, 'Message')]",
        "//form//textarea" # Generic form textarea
    ]
    for xpath in selectors:
        try: return driver.find_element(By.XPATH, xpath)
        except: continue
    return None

def mobile_js_inject(driver, element, text):
    driver.execute_script("""
        var elm = arguments[0], txt = arguments[1];
        elm.value += txt;
        elm.dispatchEvent(new Event('input', {bubbles: true}));
        elm.dispatchEvent(new Event('change', {bubbles: true}));
    """, element, text)
    
    time.sleep(0.2)
    element.send_keys(" ")
    element.send_keys(Keys.BACK_SPACE)
    time.sleep(0.5) 
    
    try:
        send_btn = driver.find_element(By.XPATH, "//div[contains(text(), 'Send')]")
        send_btn.click()
    except:
        element.send_keys(Keys.ENTER)

def run_life_cycle(agent_id, user, pw, target, messages):
    driver = None
    sent_in_this_life = 0
    session_start_time = time.time()
    last_refresh_time = time.time()
    
    try:
        log_status(agent_id, "🚀 Phoenix V34 (UI Bulldozer)...")
        driver = get_driver(agent_id)
        
        if not full_login_flow(driver, agent_id, user, pw):
            return

        target_url = f"https://www.instagram.com/direct/t/{target}/"
        log_status(agent_id, f"🔍 Navigating to Target...")
        driver.get(target_url)
        time.sleep(8) # Wait longer for Mobile UI to load
        
        # 🚜 BULLDOZER MODE: CLEAR ALL POPUPS
        clear_popups(driver, agent_id)
        time.sleep(2)

        msg_box = find_mobile_box(driver)
        if not msg_box:
            log_status(agent_id, f"❌ ERROR: Chat box not found. URL: {driver.current_url}")
            driver.save_screenshot(f"debug_mobile_error_{agent_id}.png")
            
            # If redirected to inbox, warn user
            if "/direct/inbox/" in driver.current_url:
                 log_status(agent_id, "💀 FATAL: Redirected to Inbox! ID is wrong or blocked.")
            return

        log_status(agent_id, "✅ Target Locked. Sending...")

        while (time.time() - session_start_time) < SESSION_DURATION:
            if (time.time() - last_refresh_time) > REFRESH_INTERVAL:
                log_status(agent_id, "♻️ RAM Soft Refresh...")
                driver.refresh()
                time.sleep(8)
                clear_popups(driver, agent_id)
                msg_box = find_mobile_box(driver)
                if not msg_box: break
                last_refresh_time = time.time()

            try:
                for _ in range(BURST_SIZE):
                    msg = random.choice(messages)
                    jitter = " " 
                    mobile_js_inject(driver, msg_box, f"{msg}{jitter}")

                    sent_in_this_life += 1
                    with COUNTER_LOCK:
                        global GLOBAL_SENT
                        GLOBAL_SENT += 1
                    time.sleep(random.uniform(0.15, 0.25))
                
                log_speed(agent_id, sent_in_this_life, session_start_time)
                time.sleep(CYCLE_DELAY)
            except Exception as e:
                log_status(agent_id, f"⚠️ Loop Error: {e}")
                msg_box = find_mobile_box(driver)
                if not msg_box: break

    except Exception as e:
        log_status(agent_id, f"❌ Critical Crash: {e}")
    finally:
        if driver:
            try: driver.quit()
            except: pass
        try: shutil.rmtree(f"/tmp/chrome_p_{agent_id}", ignore_errors=True)
        except: pass

def agent_worker(agent_id, user, pw, target, messages):
    while True:
        run_life_cycle(agent_id, user, pw, target, messages)
        time.sleep(10)

def main():
    with open(LOG_FILE, "w") as f:
        f.write(f"--- SESSION START: {datetime.datetime.now()} ---\n")
    
    print(f"🔥 V34 UI BULLDOZER | {THREADS} THREADS", flush=True)
    
    user = os.environ.get("INSTA_USER", "").strip()
    pw = os.environ.get("INSTA_PASS", "").strip()
    target = os.environ.get("TARGET_THREAD_ID", "").strip()
    messages = os.environ.get("MESSAGES", "Hello").split("|")

    if not user or not pw: 
        print("❌ CRITICAL: Secrets Missing!")
        return

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            executor.submit(agent_worker, i+1, user, pw, target, messages)

if __name__ == "__main__":
    main()
