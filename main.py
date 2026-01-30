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

# --- V59 CONFIGURATION ---
THREADS = 2           
BASE_BURST = 20       
BASE_SPEED = 0.2      
BASE_DELAY = 1.0      
SESSION_DURATION = 1200 
REFRESH_INTERVAL = 600

GLOBAL_SENT = 0
COUNTER_LOCK = threading.Lock()

# --- GITHUB LOGGING ---
def gh_notice(msg):
    print(f"::notice::{msg}", flush=True)

def gh_group(title):
    print(f"::group::{title}", flush=True)

def gh_end_group():
    print("::endgroup::", flush=True)

def log_status(agent_id, msg):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] 🤖 Agent {agent_id}: {msg}", flush=True)

def log_speed(agent_id, current_sent, start_time, mode="Normal"):
    elapsed = time.time() - start_time
    if elapsed == 0: elapsed = 1
    speed = current_sent / elapsed
    with COUNTER_LOCK:
        total = GLOBAL_SENT
    print(f"⚡ Agent {agent_id} | {mode} | Total: {total} | Speed: {speed:.1f} msg/s", flush=True)

def get_driver(agent_id):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    mobile_emulation = {
        "deviceMetrics": { "width": 393, "height": 851, "pixelRatio": 3.0 },
        "userAgent": "Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Mobile Safari/537.36"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_v59_{agent_id}_{random.randint(100,999)}")
    
    driver = webdriver.Chrome(options=chrome_options)
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
        driver.execute_script("""
            var el = arguments[0];
            el.focus();
            document.execCommand('insertText', false, arguments[1]);
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, element, text)
        time.sleep(0.1)
        btn = driver.find_element(By.XPATH, "//div[contains(text(), 'Send')] | //button[text()='Send']")
        btn.click()
        return True
    except:
        try:
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
    recovery_mode = False
    
    try:
        gh_group(f"🚀 Agent {agent_id} Initialization")
        log_status(agent_id, "Booting V59 Robust Connector...")
        driver = get_driver(agent_id)
        
        # 🛡️ V59 FIX: ROBUST CONNECTION HANDSHAKE
        # Attempt to connect to Instagram 3 times before giving up
        connected = False
        for attempt in range(3):
            try:
                log_status(agent_id, f"Connection Attempt {attempt+1}...")
                driver.get("https://www.instagram.com/")
                
                # WAIT until domain is actually instagram.com
                WebDriverWait(driver, 10).until(
                    lambda d: "instagram.com" in d.current_url
                )
                connected = True
                break
            except Exception as e:
                log_status(agent_id, f"⚠️ Connection failed ({e}). Retrying...")
                time.sleep(2)
        
        if not connected:
            raise Exception("Failed to load Instagram.com after 3 attempts.")

        # Inject Cookie
        clean_session = extract_session_id(cookie)
        try:
            driver.add_cookie({
                'name': 'sessionid', 
                'value': clean_session, 
                'path': '/', 
                'domain': '.instagram.com'
            })
        except Exception as e:
            # Debugging info if it fails again
            current_domain = driver.execute_script("return document.domain;")
            raise Exception(f"Cookie Injection Failed. Browser is on: {current_domain}. Error: {e}")
            
        driver.refresh()
        time.sleep(4) 
        gh_end_group()

        driver.get(f"https://www.instagram.com/direct/t/{target}/")
        time.sleep(6)
        
        gh_notice(f"✅ Agent {agent_id} Connected! Starting Burst...")

        msg_box = find_mobile_box(driver)

        while (time.time() - start_time) < SESSION_DURATION:
            if (time.time() - last_refresh_time) > REFRESH_INTERVAL:
                gh_group(f"♻️ Agent {agent_id} Maintenance")
                log_status(agent_id, "Refreshing Memory...")
                driver.refresh()
                time.sleep(5)
                msg_box = find_mobile_box(driver)
                last_refresh_time = time.time()
                gh_end_group()

            if not msg_box:
                msg_box = find_mobile_box(driver)
                if not msg_box:
                    time.sleep(5)
                    continue

            current_burst = 5 if recovery_mode else BASE_BURST
            current_speed = 1.0 if recovery_mode else BASE_SPEED
            current_delay = 5.0 if recovery_mode else BASE_DELAY

            success_count = 0
            for _ in range(current_burst):
                msg = random.choice(messages)
                if adaptive_inject(driver, msg_box, f"{msg} "):
                    success_count += 1
                    sent_in_this_life += 1
                    with COUNTER_LOCK:
                        global GLOBAL_SENT
                        GLOBAL_SENT += 1
                    time.sleep(current_speed)
                else:
                    break 

            if success_count == 0:
                if not recovery_mode:
                    gh_notice(f"⚠️ Agent {agent_id} Rate Limited! Entering Stealth Mode.")
                recovery_mode = True
            else:
                recovery_mode = False

            log_speed(agent_id, sent_in_this_life, start_time, "Recovery" if recovery_mode else "High-Speed")
            time.sleep(current_delay)

    except Exception as e:
        gh_notice(f"❌ Agent {agent_id} Crashed: {e}")
        log_status(agent_id, f"Detailed Error: {e}")
        # Take screenshot on crash
        try: driver.save_screenshot(f"crash_agent_{agent_id}.png")
        except: pass
    finally:
        if driver: driver.quit()

def main():
    cookie = os.environ.get("INSTA_COOKIE", "").strip()
    target = os.environ.get("TARGET_THREAD_ID", "").strip()
    messages = os.environ.get("MESSAGES", "Hello").split("|")
    
    if not cookie:
        gh_notice("❌ Error: INSTA_COOKIE Secret is Missing!")
        sys.exit(1)

    gh_notice("🔥 Phoenix V59 Started | 2 Threads | Robust Connection")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            executor.submit(run_life_cycle, i+1, cookie, target, messages)

if __name__ == "__main__":
    main()
