import json
import time
import requests
import os
import sys
from playwright.sync_api import sync_playwright

# COLIS CONFIG
NUM_COLIS = ""

# RESEND CONFIG
RESEND_API_KEY = ""

# MAIL CONFIG
FROM_EMAIL = ""
TO_EMAIL = ""

# TOKEN TLGRM
TG_TOKEN = ""
TG_CHAT_ID = "" 

CHECK_INTERVAL = 240 # SCAN INTERVAL ( IN SECONDS)
TRACKING_FILE = "tracking.json"

def send_telegram(message):
    """TELEGRAM MESSAGE"""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Erreur Telegram : {e}")

def send_resend_email(new_status, history):
    """GMAIL MAIL"""
    url = "https://api.resend.com/emails"
    headers = {"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"}
    history_html = "".join([f"<li><b>{s['date']}</b> : {s['evenement']}</li>" for s in history])
    
    payload = {
        "from": FROM_EMAIL,
        "to": [TO_EMAIL],
        "subject": f"NEW INFORMATION : {new_status}",
        "html": f"<h3>Package update {NUM_COLIS}</h3><p><b>{new_status}</b></p><ul>{history_html}</ul>"
    }
    try:
        requests.post(url, headers=headers, json=payload)
    except Exception as e:
        print(f"Mail Error : {e}")

def get_tracking_data():
    """Error Telegram Sender"""
    url = f"https://colisprive.com/moncolis/pages/detailColis.aspx?numColis={NUM_COLIS}&lang=fr"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_selector(".tableHistoriqueColis", timeout=20000)
            
            rows = page.locator("tr.bandeauText").all()
            history = []
            for row in rows:
                cells = row.locator("td").all()
                if len(cells) >= 2:
                    history.append({
                        "date": cells[0].inner_text().strip(),
                        "evenement": cells[1].inner_text().strip()
                    })
            return history
        except Exception as e:
            error_msg = f"<b>Scan Error</b>\nImpossible to scrapp package\n\n<code>{str(e)[:200]}</code>"
            send_telegram(error_msg)
            return None
        finally:
            browser.close()

def main():
    print(f"Start... {NUM_COLIS}")
    send_telegram(f" <b>Bot Launch at</b>\nPackage : <code>{NUM_COLIS}</code>")
    
    while True:
        current_history = get_tracking_data()
        
        if current_history:
            last_status = current_history[0]['evenement']
            steps_text = "\n".join([f"• {s['date']} : {s['evenement']}" for s in current_history[:5]])
            
            tg_msg = f"<b>Package Colis Privé</b>\n"
            tg_msg += f"Statut : <code>{last_status}</code>\n\n"
            tg_msg += f"<b>Last steps :</b>\n{steps_text}"
            
            old_history = []
            if os.path.exists(TRACKING_FILE):
                try:
                    with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
                        old_history = json.load(f)
                except: pass

            if len(current_history) > len(old_history):
                send_telegram(f" <b>NEW STATUS DETECTED !</b>\nNew step added to history.")
                
                with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
                    json.dump(current_history, f, indent=4, ensure_ascii=False)
                
                send_resend_email(last_status, current_history)
                tg_msg += "\n\n <i>Email Send Alert !</i>"
            
            send_telegram(tg_msg)
            print(f"[{time.strftime('%H:%M:%S')}] Scan : {last_status}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
