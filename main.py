# -*- coding: utf-8 -*-
import os, time, random, threading, sys, tempfile, string
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options

# --- ⚡ ULTRA-STRIKE CONFIG ---
THREADS = 2 # 2 Agents per Machine (20 Machines = 40 Total Agents)
STRIKE_DELAY = 0.03 # 🔥 30ms (Ultimate Speed)
MACHINE_ID = os.environ.get("MACHINE_ID", "1")

def get_driver(agent_id):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=400,300")
    options.add_argument("--blink-settings=imagesEnabled=false")
    
    temp_dir = os.path.join(tempfile.gettempdir(), f"v100_u_m{MACHINE_ID}_a{agent_id}")
    options.add_argument(f"--user-data-dir={temp_dir}")
    
    driver = webdriver.Chrome(options=options)
    stealth(driver, languages=["en-US"], vendor="Google Inc.", platform="Win32", fix_hairline=True)
    return driver

def entropy_pulse(driver, text):
    """JS Pulse with Integrated Entropy (Random Numbers + Hex)."""
    try:
        # Generate a random 6-digit hex string for uniqueness
        salt = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        # Add a large random number
        rand_num = random.randint(100000, 999999)
        
        final_text = f"{text} [{rand_num}]-{salt}"
        
        driver.execute_script("""
            const box = document.querySelector('div[role="textbox"], textarea');
            if (box) {
                box.focus();
                document.execCommand('insertText', false, arguments[0]);
                box.dispatchEvent(new Event('input', { bubbles: true }));
                box.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
            }
        """, final_text)
        return True
    except: return False

def run_agent(agent_id, cookie, target, messages):
    # Long stagger (10s) to prevent 20 machines from hitting login at once
    time.sleep(agent_id * 10 + (int(MACHINE_ID) * 2)) 
    
    while True:
        driver = None
        try:
            driver = get_driver(agent_id)
            driver.get("https://www.instagram.com/")
            driver.add_cookie({'name': 'sessionid', 'value': cookie.strip(), 'domain': '.instagram.com'})
            driver.get(f"https://www.instagram.com/direct/t/{target}/")
            
            time.sleep(15) # UI Handshake
            print(f"✅ [M{MACHINE_ID}-A{agent_id}] ARMED & SALTED", flush=True)

            start = time.time()
            while (time.time() - start) < 300: # 5-minute cycles
                msg = random.choice(messages)
                if entropy_pulse(driver, msg):
                    sys.stdout.write(f"🚀")
                    sys.stdout.flush()
                time.sleep(STRIKE_DELAY)
        except: pass
        finally:
            if driver: driver.quit()
            time.sleep(5)

def main():
    cookie = os.environ.get("INSTA_COOKIE", "").strip()
    target = os.environ.get("TARGET_THREAD_ID", "").strip()
    messages = os.environ.get("MESSAGES", "PHOENIX").split("|")
    
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            executor.submit(run_agent, i+1, cookie, target, messages)

if __name__ == "__main__":
    main()
