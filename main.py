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
    
    # 🚨 V37: NO INCOGNITO (Standard Profile)
    # We want cookies to stick briefly for the warm-up strategy
    
    # MANUAL MOBILE METRICS (Pixel 5)
    mobile_emulation = {
        "deviceMetrics": { "width": 393, "height": 851, "pixelRatio": 3.0 },
        "userAgent": "Mozilla/5.0 (Linux; Android 12; Pixel 5 Build/SP1A.210812.016.A1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Randomize temp folder
    chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_v37_{agent_id}_{random.randint(100,999)}")
    return webdriver.Chrome(options=chrome_options)

def clear_popups(driver):
    popups = [
        "//button[text()='Not Now']",
        "//button[text()='Cancel']",
        "//div[text()='Not now']",
        "//button[contains(text(), 'Allow all cookies')]",
        "//button[contains(text(), 'Decline optional cookies')]"
    ]
    for xpath in popups:
        try:
            btn = driver.find_element(By.XPATH, xpath)
            btn.click()
            time.sleep(1)
        except: pass

def warm_up_and_relogin(driver, agent_id, username, password, cookie):
    """
    V37 STRATEGY:
    1. Inject Cookie -> Refresh (Warm up device trust)
    2. Logout Manually
    3. Login with Password
    """
    
    # --- STEP 1: COOKIE WARM UP ---
    log_status(agent_id, "🍪 Phase 1: Cookie Warm-Up...")
    driver.get("https://www.instagram.com/")
    time.sleep(3)
    
    if cookie:
        try:
            clean_session = cookie.split("sessionid=")[1].split(";")[0] if "sessionid=" in cookie else cookie
            driver.add_cookie({'name': 'sessionid', 'value': clean_session, 'path': '/'})
        except:
            log_status(agent_id, "⚠️ Invalid Cookie Format. Skipping Warm-up.")

    driver.refresh()
    time.sleep(5)
    
    # 📸 SNAPSHOT 1: Did cookie work?
    driver.save_screenshot(f"debug_1_cookie_result_agent_{agent_id}.png")

    # --- STEP 2: FORCED LOGOUT ---
    log_status(agent_id, "👋 Phase 2: Forcing Clean Logout...")
    driver.get("https://www.instagram.com/accounts/logout/")
    time.sleep(8)
    
    # 📸 SNAPSHOT 2: Are we at login page?
    driver.save_screenshot(f"debug_2_logout_result_agent_{agent_id}.png")

    # --- STEP 3: FRESH LOGIN ---
    log_status(agent_id, "🔑 Phase 3: Fresh Login Attempt...")
    
    # Ensure we are at login URL
    if "login" not in driver.current_url:
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(5)

    clear_popups(driver)

    try:
        user_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        user_input.send_keys(username)
        time.sleep(1)
        
        pass_input = driver.find_element(By.NAME, "password")
        pass_input.send_keys(password)
        time.sleep(1)
        
        # Click Login
        try:
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
        except:
            pass_input.send_keys(Keys.ENTER)
            
        log_status(agent_id, "⏳ Verifying Login...")
        time.sleep(10)
        
        # 📸 SNAPSHOT 3: Did login succeed?
        driver.save_screenshot(f"debug_3_login_result_agent_{agent_id}.png")
        
        if "login" in driver.current_url or "challenge" in driver.current_url:
            log_status(agent_id, "❌ Login Failed (Challenge or Bad Pass).")
            return False
            
        log_status(agent_id, "✅ Login Success!")
        return True

    except Exception as e:
        log_status(agent_id, f"❌ Login Exception: {e}")
        driver.save_screenshot(f"debug_error_login_agent_{agent_id}.png")
        return False

def find_mobile_box(driver):
    selectors = [
        "//textarea", 
        "//div[@role='textbox']",
        "//div[contains(@aria-label, 'Message')]"
    ]
    for xpath in selectors:
        try: return driver.find_element(By.XPATH, xpath)
        except: continue
    return None

def mobile_js_inject(driver, element, text):
    # Safe injection
    driver.execute_script("""
        var elm = arguments[0], txt = arguments[1];
        elm.value = txt;
        elm.dispatchEvent(new Event('input', {bubbles: true}));
    """, element, text)
    time.sleep(0.5)
    element.send_keys(" ")
    element.send_keys(Keys.BACK_SPACE)
    time.sleep(0.5) 
    try:
        send_btn = driver.find_element(By.XPATH, "//div[contains(text(), 'Send')] | //button[text()='Send']")
        send_btn.click()
    except:
        element.send_keys(Keys.ENTER)

def run_life_cycle(agent_id, user, pw, cookie, target, messages):
    driver = None
    sent_in_this_life = 0
    start_time = time.time()
    
    try:
        log_status(agent_id, "🚀 Phoenix V37 (Warm-Up Protocol)...")
        driver = get_driver(agent_id)
        
        # Run the V37 Logic
        if not warm_up_and_relogin(driver, agent_id, user, pw, cookie):
            return

        target_url = f"https://www.instagram.com/direct/t/{target}/"
        log_status(agent_id, "🔍 Navigating to Target...")
        driver.get(target_url)
        time.sleep(8)
        
        clear_popups(driver)
        msg_box = find_mobile_box(driver)
        
        if not msg_box:
            log_status(agent_id, "❌ Chat box not found.")
            # 📸 SNAPSHOT 4: Why is box missing?
            driver.save_screenshot(f"debug_4_box_missing_agent_{agent_id}.png")
            
            if "/inbox" in driver.current_url:
                log_status(agent_id, "💀 FATAL: Redirected to Inbox. ID is Invalid!")
            return

        log_status(agent_id, "✅ Target Locked. Sending...")

        while (time.time() - start_time) < SESSION_DURATION:
            try:
                for _ in range(BURST_SIZE):
                    msg = random.choice(messages)
                    mobile_js_inject(driver, msg_box, f"{msg} ")
                    sent_in_this_life += 1
                    with COUNTER_LOCK:
                        global GLOBAL_SENT
                        GLOBAL_SENT += 1
                    time.sleep(random.uniform(0.1, 0.3))
                
                log_speed(agent_id, sent_in_this_life, start_time)
                time.sleep(CYCLE_DELAY)
            except:
                break

    except Exception as e:
        log_status(agent_id, f"❌ Agent Crash: {e}")
    finally:
        if driver: driver.quit()

def agent_worker(agent_id, user, pw, cookie, target, messages):
    while True:
        run_life_cycle(agent_id, user, pw, cookie, target, messages)
        time.sleep(10)

def main():
    with open(LOG_FILE, "w") as f: f.write("PHOENIX V37 START\n")
    print("🔥 V37 WARM-UP PROTOCOL | STANDING BY", flush=True)
    
    user = os.environ.get("INSTA_USER", "").strip()
    pw = os.environ.get("INSTA_PASS", "").strip()
    cookie = os.environ.get("INSTA_COOKIE", "").strip() # Needed for Warm-up
    target = os.environ.get("TARGET_THREAD_ID", "").strip()
    messages = os.environ.get("MESSAGES", "Hello").split("|")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            executor.submit(agent_worker, i+1, user, pw, cookie, target, messages)

if __name__ == "__main__":
    main()
