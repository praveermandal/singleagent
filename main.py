import os
import time
import re
import random
import datetime
import threading
import sys
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- V64 CONFIGURATION ---
THREADS = 1             # ⚠️ KEEP AT 1 TO AVOID BANS
BASE_BURST = 5          # Lower burst to be safer
BASE_SPEED = 0.5        # Slower typing to look human
SESSION_DURATION = 1200 # 20 Minutes per run
REFRESH_INTERVAL = 600  # Refresh every 10 mins

GLOBAL_SENT = 0
COUNTER_LOCK = threading.Lock()

def gh_notice(msg):
    print(f"::notice::{msg}", flush=True)

def log_status(agent_id, msg):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] 🤖 Agent {agent_id}: {msg}", flush=True)

def get_driver(agent_id):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # Block Images (Speed + RAM Saver)
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Stealth Args
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # Mobile Emulation (Pixel 5)
    mobile_emulation = {
        "deviceMetrics": { "width": 393, "height": 851, "pixelRatio": 3.0 },
        "userAgent": "Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Mobile Safari/537.36"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_v64_{agent_id}_{random.randint(100,999)}")
    
    driver = webdriver.Chrome(options=chrome_options)
    # CDP Patch to hide 'navigator.webdriver'
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def find_mobile_box(driver):
    selectors = ["//textarea", "//div[@role='textbox']", "//div[@contenteditable='true']"]
    for xpath in selectors:
        try: 
            el = driver.find_element(By.XPATH, xpath)
            if el.is_displayed(): return el
        except: continue
    return None

def adaptive_inject(driver, element, text):
    try:
        element.click()
        # Native JS Injection (Reliable)
        driver.execute_script("""
            var el = arguments[0];
            el.focus();
            document.execCommand('insertText', false, arguments[1]);
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, element, text)
        
        time.sleep(0.1)
        
        # Try finding Send button
        try:
            btn = driver.find_element(By.XPATH, "//div[contains(text(), 'Send')] | //button[text()='Send']")
            btn.click()
        except:
            element.send_keys(Keys.ENTER)
        return True
    except:
        return False

def extract_session_id(raw_cookie):
    match = re.search(r'sessionid=([^;]+)', raw_cookie)
    return match.group(1).strip() if match else raw_cookie.strip()

def run_life_cycle(agent_id, cookie, target, messages):
    driver = None
    sent_in_this_life = 0
    start_time = time.time()
    last_refresh_time = time.time()
    
    try:
        log_status(agent_id, "Booting V64 Core...")
        driver = get_driver(agent_id)
        
        # 🛡️ ROBUST CONNECTION (3 Retries)
        connected = False
        for attempt in range(3):
            try:
                driver.get("https://www.instagram.com/")
                WebDriverWait(driver, 10).until(lambda d: "instagram.com" in d.current_url)
                connected = True
                break
            except:
                time.sleep(2)
        
        if not connected:
            raise Exception("Failed to reach Instagram.com")

        # Inject Cookie
        clean_session = extract_session_id(cookie)
        driver.add_cookie({'name': 'sessionid', 'value': clean_session, 'path': '/', 'domain': '.instagram.com'})
        driver.refresh()
        time.sleep(4) 
        
        # Navigate to Chat
        driver.get(f"https://www.instagram.com/direct/t/{target}/")
        time.sleep(6)
        
        gh_notice(f"✅ Agent {agent_id} Connected. Loop Started.")
        msg_box = find_mobile_box(driver)

        while (time.time() - start_time) < SESSION_DURATION:
            # ♻️ Maintenance Cycle (Every 10 mins)
            if (time.time() - last_refresh_time) > REFRESH_INTERVAL:
                log_status(agent_id, "Refreshing Memory...")
                driver.refresh()
                time.sleep(5)
                msg_box = find_mobile_box(driver)
                last_refresh_time = time.time()

            if not msg_box:
                msg_box = find_mobile_box(driver)
                if not msg_box:
                    time.sleep(5)
                    continue

            # Send Message
            msg = random.choice(messages)
            if adaptive_inject(driver, msg_box, f"{msg} "):
                sent_in_this_life += 1
                with COUNTER_LOCK:
                    global GLOBAL_SENT
                    GLOBAL_SENT += 1
                log_status(agent_id, f"Sent: {msg}")
            
            time.sleep(BASE_SPEED)

    except Exception as e:
        log_status(agent_id, f"❌ Error: {e}")
    finally:
        if driver: driver.quit()

def main():
    cookie = os.environ.get("INSTA_COOKIE", "").strip()
    target = os.environ.get("TARGET_THREAD_ID", "").strip()
    messages = os.environ.get("MESSAGES", "Hello").split("|")
    
    if not cookie:
        sys.exit(1)

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            executor.submit(run_life_cycle, i+1, cookie, target, messages)

if __name__ == "__main__":
    main()
