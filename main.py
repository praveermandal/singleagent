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
    
    # 🚨 V35 FIX: INCOGNITO & CLEAN PROFILE
    chrome_options.add_argument("--incognito")
    
    # MANUAL MOBILE METRICS (Pixel 5)
    mobile_emulation = {
        "deviceMetrics": { "width": 393, "height": 851, "pixelRatio": 3.0 },
        "userAgent": "Mozilla/5.0 (Linux; Android 12; Pixel 5 Build/SP1A.210812.016.A1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Randomized temp folder to ensure no cache overlap
    chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_v35_{agent_id}_{random.randint(100,999)}")
    return webdriver.Chrome(options=chrome_options)

def clear_popups(driver, agent_id):
    popups = [
        "//button[text()='Not Now']",
        "//button[text()='Cancel']",
        "//div[text()='Not now']",
        "//button[contains(text(), 'Allow all cookies')]", # Essential for login
        "//button[contains(text(), 'Decline optional cookies')]"
    ]
    for xpath in popups:
        try:
            btn = driver.find_element(By.XPATH, xpath)
            btn.click()
            time.sleep(1)
        except: pass

def full_login_flow(driver, agent_id, username, password):
    log_status(agent_id, "🔑 Navigating to Clean Login Page...")
    try:
        # 🚨 V35 FIX: Clean URL (No redirects)
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(7)
        
        # Check title to see if page loaded
        log_status(agent_id, f"📄 Page Title: {driver.title}")
        
        # Check for Cookie Consent
        clear_popups(driver, agent_id)

        # 1. Wait for Username Field
        try:
            user_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            user_input.send_keys(username)
            time.sleep(random.uniform(1, 2))
        except:
            # 📸 DEBUG: If this fails, we need to know why
            log_status(agent_id, "❌ Timeout: Username field not found. Dumping page source...")
            driver.save_screenshot(f"login_timeout_agent_{agent_id}.png")
            return False

        # 2. Enter Password
        pass_input = driver.find_element(By.NAME, "password")
        pass_input.send_keys(password)
        time.sleep(1)
        pass_input.send_keys(Keys.ENTER)
            
        log_status(agent_id, "⏳ Waiting for Login Confirmation...")
        time.sleep(12)
        
        # 3. Final Verification
        if "login" in driver.current_url:
            log_status(agent_id, "❌ Login Failed. Still at Login URL.")
            return False
            
        log_status(agent_id, "✅ Identity Mask Verified. Login Success.")
        return True

    except Exception as e:
        log_status(agent_id, f"❌ Login Exception: {e}")
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

def run_life_cycle(agent_id, user, pw, target, messages):
    driver = None
    sent_in_this_life = 0
    start_time = time.time()
    
    try:
        log_status(agent_id, "🚀 Phoenix V35.1 Booting...")
        driver = get_driver(agent_id)
        
        if not full_login_flow(driver, agent_id, user, pw):
            return

        target_url = f"https://www.instagram.com/direct/t/{target}/"
        driver.get(target_url)
        time.sleep(8)
        
        clear_popups(driver, agent_id)
        msg_box = find_mobile_box(driver)
        
        if not msg_box:
            log_status(agent_id, "❌ Chat box not found.")
            driver.save_screenshot(f"box_not_found_agent_{agent_id}.png")
            return

        log_status(agent_id, "✅ Target Locked. Commencing Transmission.")

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

def agent_worker(agent_id, user, pw, target, messages):
    while True:
        run_life_cycle(agent_id, user, pw, target, messages)
        time.sleep(10)

def main():
    with open(LOG_FILE, "w") as f: f.write("PHOENIX V35.1 START\n")
    print("🔥 V35.1 IDENTITY MASK | STANDING BY", flush=True)
    
    user = os.environ.get("INSTA_USER", "").strip()
    pw = os.environ.get("INSTA_PASS", "").strip()
    target = os.environ.get("TARGET_THREAD_ID", "").strip()
    messages = os.environ.get("MESSAGES", "Hello").split("|")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            executor.submit(agent_worker, i+1, user, pw, target, messages)

if __name__ == "__main__":
    main()
