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
BURST_SIZE = 10       
BURST_DELAY = 1.0     
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
    
    mobile_emulation = {
        "deviceMetrics": { "width": 393, "height": 851, "pixelRatio": 3.0 },
        "userAgent": "Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Mobile Safari/537.36"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_v47_{agent_id}_{random.randint(100,999)}")
    return webdriver.Chrome(options=chrome_options)

def clear_overlays(driver):
    """
    🔥 V47: BLIND ESCAPER
    Presses ESC and clicks coordinate (10,10) to dismiss invisible modals.
    """
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        ActionChains(driver).move_by_offset(10, 10).click().perform()
    except: pass
    
    # Specific buttons
    popups = [
        "//button[text()='Not Now']",
        "//button[text()='Cancel']",
        "//div[text()='Not now']",
        "//button[contains(text(), 'Use the App')]/following-sibling::button"
    ]
    for xpath in popups:
        try:
            driver.find_element(By.XPATH, xpath).click()
            time.sleep(0.3)
        except: pass

def find_mobile_box(driver):
    """
    🔥 V47: OMNI-SELECTOR
    Looks for ANY valid input method.
    """
    selectors = [
        "//textarea", 
        "//div[@role='textbox']",
        "//div[@contenteditable='true']",
        "//input[@type='text']",
        "//form//textarea"
    ]
    for xpath in selectors:
        try: 
            el = driver.find_element(By.XPATH, xpath)
            if el.is_displayed():
                return el
        except: continue
    return None

def verify_and_send(driver, element, text):
    # METHOD A: Type
    try:
        element.click()
        element.send_keys(text)
    except: pass
    
    time.sleep(0.2)
    
    # METHOD B: JS Backup
    try:
        # Check if empty (works for textarea)
        val = element.get_attribute("value")
        # Check text (works for div)
        txt = element.text
        
        if (not val and not txt):
            driver.execute_script("arguments[0].innerText = arguments[1];", element, text)
            time.sleep(0.1)
    except: pass
    
    # SEND
    try:
        btn = driver.find_element(By.XPATH, "//div[contains(text(), 'Send')] | //button[text()='Send']")
        btn.click()
        return True
    except:
        element.send_keys(Keys.ENTER)
        return True

def run_life_cycle(agent_id, cookie, target, messages):
    driver = None
    sent_in_this_life = 0
    start_time = time.time()
    
    try:
        log_status(agent_id, "🚀 Phoenix V47 (Omni-Selector)...")
        driver = get_driver(agent_id)
        
        driver.get("https://www.instagram.com/")
        time.sleep(3)
        
        if cookie:
            try:
                clean = cookie.split("sessionid=")[1].split(";")[0].strip() if "sessionid=" in cookie else cookie.strip()
                driver.add_cookie({'name': 'sessionid', 'value': clean, 'path': '/', 'domain': '.instagram.com'})
            except: return
        
        driver.refresh()
        time.sleep(5)
        
        target_url = f"https://www.instagram.com/direct/t/{target}/"
        log_status(agent_id, "🔍 Navigating...")
        driver.get(target_url)
        time.sleep(8)
        
        # 🚨 V47: Clear Overlays before searching
        clear_overlays(driver)
        
        msg_box = find_mobile_box(driver)
        
        if not msg_box:
            log_status(agent_id, f"❌ Box not found. Current URL: {driver.current_url}")
            driver.save_screenshot(f"box_missing_{agent_id}.png")
            return

        log_status(agent_id, "✅ Target Locked. Sending...")

        while (time.time() - start_time) < SESSION_DURATION:
            try:
                for _ in range(BURST_SIZE):
                    msg = random.choice(messages)
                    verify_and_send(driver, msg_box, f"{msg} ")
                    
                    sent_in_this_life += 1
                    with COUNTER_LOCK:
                        global GLOBAL_SENT
                        GLOBAL_SENT += 1
                    
                    time.sleep(BURST_DELAY)
                
                log_speed(agent_id, sent_in_this_life, start_time)
                time.sleep(CYCLE_DELAY)
            except:
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
    print("🔥 V47 OMNI-SELECTOR | STARTING", flush=True)
    cookie = os.environ.get("INSTA_COOKIE", "").strip()
    target = os.environ.get("TARGET_THREAD_ID", "").strip()
    messages = os.environ.get("MESSAGES", "Hello").split("|")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            executor.submit(agent_worker, i+1, cookie, target, messages)

if __name__ == "__main__":
    main()
