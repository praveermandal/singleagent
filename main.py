# -*- coding: utf-8 -*-
# 🚀 PHOENIX V100.40 (JS-HYPER-INJECT)
# 🛡️ BY PRAVEERFUCKS | 100-AGENT BURST (FREE TIER OPTIMIZED)
# ⚡ SPEED: 10ms NATIVE JS PULSE | 5 TABS PER RUNNER

import os, time, random, sys, string
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- ⚡ HYPER-INJECT CONFIG ---
TABS_PER_MACHINE = 5  # 20 Machines x 5 Tabs = 100 Agents total

def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.page_load_strategy = 'eager'
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--blink-settings=imagesEnabled=false")
    
    # iPad Pro emulation for the fastest Lexical DOM response
    options.add_experimental_option("mobileEmulation", {"deviceName": "iPad Pro"})
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(options=options, service=service)

def main():
    cookie = os.environ.get("INSTA_COOKIE")
    target = os.environ.get("TARGET_THREAD_ID")
    msg_list = os.environ.get("MESSAGES", "STRIKE|ACTIVE").split("|")
    machine_id = os.environ.get("MACHINE_ID", "1")

    driver = get_driver()
    try:
        # 1. Login Handshake
        driver.get("https://www.instagram.com/")
        driver.add_cookie({'name': 'sessionid', 'value': cookie.strip(), 'domain': '.instagram.com'})
        
        # 2. Launch Hyper-Tabs
        print(f"🚀 MACHINE {machine_id}: Launching {TABS_PER_MACHINE} Hyper-Tabs...")
        for i in range(TABS_PER_MACHINE):
            driver.execute_script(f"window.open('https://www.instagram.com/direct/t/{target}/', '_blank');")
            time.sleep(6) # Safe stagger for hydration

        handles = driver.window_handles[1:] # Ignore main page
        
        # 3. ⚡ THE INJECTION: Deploy JS Engine into every tab
        for handle in handles:
            driver.switch_to.window(handle)
            driver.execute_script("""
                const messages = arguments[0];
                console.log("🚀 JS-ENGINE DEPLOYED");
                
                setInterval(() => {
                    const box = document.querySelector('div[role="textbox"], [contenteditable="true"]');
                    if (box) {
                        // Select random message and add high-speed salt
                        const rawMsg = messages[Math.floor(Math.random() * messages.length)];
                        const salt = Math.random().toString(36).substring(7);
                        const finalText = `${rawMsg} [${salt}]`;

                        // High-Speed Lexical Injection
                        box.focus();
                        document.execCommand('insertText', false, finalText);
                        box.dispatchEvent(new Event('input', { bubbles: true }));

                        // Native Keyboard Dispatch
                        const enter = new KeyboardEvent('keydown', {
                            bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13
                        });
                        box.dispatchEvent(enter);

                        // Prevent DOM heavy-load
                        setTimeout(() => { box.innerHTML = ""; }, 2);
                    }
                }, 15); // 15ms pulse = Insane speed
            """, msg_list)
        
        print(f"🔥 MACHINE {machine_id}: ALL TABS FIRING AT 15ms PULSE.")
        
        # 4. Keep alive and monitor
        while True:
            time.sleep(60)
            # Periodic refresh of the first tab to prevent runner idle timeout
            driver.switch_to.window(handles[0])
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    except Exception as e:
        print(f"⚠️ FATAL: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
