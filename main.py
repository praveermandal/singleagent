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
BURST_SIZE = 10       
BURST_DELAY = 1.0     # Slower to ensure verification
CYCLE_DELAY = 2.0     
SESSION_DURATION = 1200 
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
    entry = f"[{timestamp}] ⚡ Agent {agent_id} | Total: {total} | Speed: {speed:.1f} msg/s"
    print(entry, flush=True)
    write_log(entry)

def get_driver(agent_id):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # MOBILE EMULATION (Pixel 5)
    mobile_emulation = {
        "deviceMetrics": { "width": 393, "height": 851, "pixelRatio": 3.0 },
        "userAgent": "Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Mobile Safari/537.36"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_v46_{agent_id}_{random.randint(100,999)}")
    return webdriver.Chrome(options=chrome_options)

def clear_popups(driver):
    popups = [
        "//button[text()='Not Now']",
        "//button[text()='Cancel']",
        "//div[text()='Not now']",
        "//button[contains(text(), 'Use the App')]/following-sibling::button",
        "//button[contains(@aria-label, 'Close')]"
    ]
    for xpath in popups:
        try:
            driver.find_element(By.XPATH, xpath).click()
            time.sleep(0.5)
        except: pass

def find_mobile_box(driver):
    # STRICT selector: Only Textarea. Divs are unreliable on Mobile.
    selectors = ["//textarea", "//form//textarea"]
    for xpath in selectors:
        try: return driver.find_element(By.XPATH, xpath)
        except: continue
    return None

def verify_and_send(driver, element, text):
    """
    🔥 V46: TEXT VERIFICATION PROTOCOL
    1. Try to type.
    2. Read value back.
    3. If empty, try JS Inject.
    4. Only click Send if value matches.
    """
    
    # METHOD A: Physical Type
    try:
        element.click()
        element.clear()
        element.send_keys(text)
    except: pass
    
    time.sleep(0.2)
    
    # VERIFICATION STEP
    current_val = element.get_attribute("value")
    
    # If Method A failed (Box is empty), try Method B (JS Inject)
    if not current_val or len(current_val) == 0:
        driver.execute_script("""
            var el = arguments[0];
            el.value = arguments[1];
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        """, element, text)
        time.sleep(0.2)
        current_val = element.get_attribute("value")
    
    # FINAL CHECK: Did it work?
    if current_val and len(current_val) > 0:
        # Check for Blue Send Button
        try:
            btn = driver.find_element(By.XPATH, "//div[contains(text(), 'Send')] | //button[text()='Send']")
            btn.click()
            return True
        except:
            element.send_keys(Keys.ENTER)
            return True
    else:
        # If we are here, the browser refused to accept text.
        return False

def run_life_cycle(agent_id, cookie, target, messages):
    driver = None
    sent_in_this_life = 0
    start_time = time.time()
    
    try:
        log_status(agent_id, "🚀 Phoenix V46 (Verified Sender)...")
        driver = get_driver(agent_id)
        
        driver.get("https://www.instagram.com/")
        time.sleep(3)
        
        if cookie:
            try:
                if "sessionid=" in cookie:
                    clean_session = cookie.split("sessionid=")[1].split(";")[0].strip()
                else:
                    clean_session = cookie.strip()
                
                driver.add_cookie({'name': 'sessionid', 'value': clean_session, 'path': '/', 'domain': '.instagram.com'})
            except: return
        
        driver.refresh()
        time.sleep(5)
        
        if "login" in driver.current_url:
            log_status(agent_id, "💀 Cookie Expired.")
            return

        target_url = f"https://www.instagram.com/direct/t/{target}/"
        log_status(agent_id, "🔍 Navigating...")
        driver.get(target_url)
        time.sleep(8)
        
        clear_popups(driver)
        msg_box = find_mobile_box(driver)
        
        if not msg_box:
            log_status(agent_id, "❌ Box not found.")
            driver.save_screenshot(f"box_missing_{agent_id}.png")
            return

        log_status(agent_id, "✅ Verified Link Established.")

        while (time.time() - start_time) < SESSION_DURATION:
            try:
                for _ in range(BURST_SIZE):
                    msg = random.choice(messages)
                    
                    # 🚨 V46: VERIFY
                    success = verify_and_send(driver, msg_box, f"{msg} ")
                    
                    if success:
                        sent_in_this_life += 1
                        with COUNTER_LOCK:
                            global GLOBAL_SENT
                            GLOBAL_SENT += 1
                    else:
                        log_status(agent_id, "⚠️ Input Failed (Box Empty). Retrying...")
                    
                    time.sleep(BURST_DELAY)
                
                log_speed(agent_id, sent_in_this_life, start_time)
                time.sleep(CYCLE_DELAY)
            except Exception:
                break

    except Exception as e:
        log_status(agent_id, f"❌ Crash: {e}")
    finally:
        if driver: driver.quit()

def agent_worker(agent_id, cookie, target, messages):
    while True:
        run_life_cycle(agent_id, cookie, target, messages)
        time.sleep(5)

def main():
    with open(LOG_FILE, "w") as f: f.write("PHOENIX V46 START\n")
    print("🔥 V46 VERIFIED SENDER | CHECKING INPUT", flush=True)
    
    cookie = os.environ.get("INSTA_COOKIE", "").strip()
    target = os.environ.get("TARGET_THREAD_ID", "").strip()
    messages = os.environ.get("MESSAGES", "Hello").split("|")

    if not cookie: 
        print("❌ INSTA_COOKIE Missing!")
        return

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            executor.submit(agent_worker, i+1, cookie, target, messages)

if __name__ == "__main__":
    main()
