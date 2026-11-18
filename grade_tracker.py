import os
import time
import hashlib
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- THIS INFORMATIONS WILL COME FROM GITHUB ---
#We will get this informations from Github Secrets
KULLANICI_ADI = os.environ["OKUL_NO"]
SIFRE = os.environ["OKUL_SIFRE"]
TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]

# --- CUSTOM SETTINGS  ---
LOGIN_URL = "https://sabis.sakarya.edu.tr/"
NOT_URL = "https://obs.sabis.sakarya.edu.tr/Ders"

# ID'S
ID_USER_1 = "UserName" 
ID_PASS_1 = "Password" 
ID_BTN_1  = "btnLogin"
ID_USER_2 = "Username" 
ID_PASS_2 = "Password" 
XPATH_BTN_2 = '//*[@id="kt_login_form"]/div[4]/button' 

def telegram_gonder(mesaj):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      data={"chat_id": TG_CHAT_ID, "text": mesaj})
    except: pass

def butona_tikla_idsiz(driver):
    """Yedek tıklama yöntemleri"""
    try: driver.find_element(By.XPATH, XPATH_BTN_2).click(); return
    except: pass
    try: driver.find_element(By.XPATH, "//button[@type='submit']").click(); return
    except: pass
    try: driver.find_element(By.XPATH, "//*[contains(text(), 'Giriş')]").click(); return
    except: pass

def main():
    # --- HEADLESS MODE SETTINGS ---
    chrome_options = Options()
    chrome_options.add_argument("--headless") # HEADLESS MODE
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # FIRST LOGIN
        print("Giriş yapılıyor...")
        driver.get(LOGIN_URL)
        time.sleep(3)
        driver.find_element(By.ID, ID_USER_1).send_keys(KULLANICI_ADI)
        driver.find_element(By.ID, ID_PASS_1).send_keys(SIFRE)
        driver.find_element(By.ID, ID_BTN_1).click()
        time.sleep(5)

        # NOTE AND  DUAL LOGIN CONTROL
        driver.get(NOT_URL)
        time.sleep(5)

        if len(driver.find_elements(By.ID, ID_USER_2)) > 0:
            print("İkinci giriş ekranı aşılyor...")
            driver.find_element(By.ID, ID_USER_2).send_keys(KULLANICI_ADI)
            driver.find_element(By.ID, ID_PASS_2).send_keys(SIFRE)
            butona_tikla_idsiz(driver)
            time.sleep(5)

        # PULL DATA
        time.sleep(3) 
        yeni_veri = driver.find_element(By.TAG_NAME, "body").text
            
        # COMPARE WITH LAST DATA
        yeni_hash = hashlib.md5(yeni_veri.encode('utf-8')).hexdigest()

        eski_hash = ""
        # Dosya varsa eski hash'i oku
        if os.path.exists("son_durum.txt"):
            with open("son_durum.txt", "r", encoding="utf-8") as f:
                eski_hash = f.read().strip()

        if yeni_hash != eski_hash:
            print(f"Değişiklik var! (Yeni Hash: {yeni_hash})")
            
            # Eğer dosya boş değilse (ilk çalışma değilse) bildirim at
            if eski_hash != "":
                telegram_gonder("🚨 OBS BOTU: Notlarında değişiklik var! Hemen kontrol et.")
            
            # Dosyaya notları DEĞİL, sadece HASH kodunu kaydet (Gizlilik için)
            with open("son_durum.txt", "w", encoding="utf-8") as f:
                f.write(yeni_hash)
        else:
            print("Değişiklik yok (Hash aynı).")

    except Exception as e:
    print(f"Hata oluştu: {e}")
    raise
    finally:
        driver.quit()

if __name__ == "__main__":
    main()



