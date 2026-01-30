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

# --- VELOCITY CONFIGURATION ---
THREADS = 2           
BURST_SIZE = 15       # ⬆️ Increased for continuous fire
BURST_DELAY = 0.2     # ⬇️ Reduced pause between messages
CYCLE_DELAY = 1.0     # ⬇️ Shortened breather between bursts
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
    
    chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_v42_1_{agent_id}_{random.randint(100,999)}")
    return webdriver.Chrome(options=chrome_options)

def clear_popups(driver):
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
    selectors = ["//textarea", "//div[@role='textbox']", "//div[contains(@aria-label, 'Message')]"]
    for xpath in selectors:
        try: return driver.find_element(By.XPATH, xpath)
        except: continue
    return None

def velocity_type(driver, element, text):
    """
    ⚡ HIGH-VELOCITY PHYSICAL TYPING
    """
    try:
        # Standard typing (Faster than JS injection for React recognition)
        element.send_keys(text)
        
        # Immediate attempt to find and click Send
        try:
            # We look for the blue 'Send' text button
            send_btn = driver.find_element(By.XPATH, "//div[contains(text(), 'Send')] | //button[text()='Send']")
            send_btn.click()
        except:
            # Rapid fallback to Enter key
            element.send_keys(Keys.ENTER)
    except:
        pass

def run_life_cycle(agent_id, cookie, target, messages):
    driver = None
    sent_in_this_life = 0
    start_time = time.time()
    
    try:
        log_status(agent_id, "🚀 Phoenix V42.1 (Velocity Mode)...")
        driver = get_driver(agent_id)
        driver.get("https://www.instagram.com/")
        time.sleep(2)
        
        if cookie:
            try:
                clean_session = cookie.split("sessionid=")[1].split(";")[0].strip() if "sessionid=" in cookie else cookie.strip()
                driver.add_cookie({'name': 'sessionid', 'value': clean_session, 'path': '/', 'domain': '.instagram.com'})
            except: return
        
        driver.refresh()
        time.sleep(4)
        
        target_url = f"https://www.instagram.com/direct/t/{target}/"
        driver.get(target_url)
        time.sleep(6)
        
        clear_popups(driver)
        msg_box = find_mobile_box(driver)
        
        if not msg_box:
            log_status(agent_id, "❌ Box not found.")
            return

        log_status(agent_id, "⚡ Velocity Engaged.")

        while (time.time() - start_time) < SESSION_DURATION:
            try:
                for _ in range(BURST_SIZE):
                    msg = random.choice(messages)
                    
                    # ⚡ PHYSICAL SEND
                    velocity_type(driver, msg_box, f"{msg} ")
                    
                    sent_in_this_life += 1
                    with COUNTER_LOCK:
                        global GLOBAL_SENT
                        GLOBAL_SENT += 1
                    
                    # ⚡ Minimal gap between messages
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
        time.sleep(2)

def main():
    print("🔥 V42.1 VELOCITY TYPIST | NO JITTER", flush=True)
    cookie = os.environ.get("INSTA_COOKIE", "").strip()
    target = os.environ.get("TARGET_THREAD_ID", "").strip()
    messages = os.environ.get("MESSAGES", "Hello").split("|")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            executor.submit(agent_worker, i+1, cookie, target, messages)

if __name__ == "__main__":
    main()
