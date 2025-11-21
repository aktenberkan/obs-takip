import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- GITHUB'DAN GELECEK BİLGİLER ---
# Bu bilgileri kodun içine yazmıyoruz, GitHub Secrets'tan alacağız
KULLANICI_ADI = os.environ["OKUL_NO"]
SIFRE = os.environ["OKUL_SIFRE"]
TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]

# --- SABİT AYARLAR ---
LOGIN_URL = "https://sabis.sakarya.edu.tr/"
NOT_URL = "https://obs.sabis.sakarya.edu.tr/Ders"

# ID'LER (Senin son çalışan kodundaki ID'leri buraya yaz)
ID_USER_1 = "UserName" # Değiştir
ID_PASS_1 = "Password" # Değiştir
ID_BTN_1  = "btnLogin"   # Değiştir
ID_USER_2 = "Username" # Değiştir (2. ekran varsa)
ID_PASS_2 = "Password" # Değiştir
XPATH_BTN_2 = '//*[@id="kt_login_form"]/div[4]/button' # Değiştir

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
    # --- HEADLESS (HAYALET) MOD AYARLARI ---
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Ekransız mod
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # 1. GİRİŞ
        print("Giriş yapılıyor...")
        driver.get(LOGIN_URL)
        time.sleep(3)
        driver.find_element(By.ID, ID_USER_1).send_keys(KULLANICI_ADI)
        driver.find_element(By.ID, ID_PASS_1).send_keys(SIFRE)
        driver.find_element(By.ID, ID_BTN_1).click()
        time.sleep(5)

        # 2. NOT SAYFASI VE ÇİFT GİRİŞ KONTROLÜ
        driver.get(NOT_URL)
        time.sleep(5)

        if len(driver.find_elements(By.ID, ID_USER_2)) > 0:
            print("İkinci giriş ekranı aşılyor...")
            driver.find_element(By.ID, ID_USER_2).send_keys(KULLANICI_ADI)
            driver.find_element(By.ID, ID_PASS_2).send_keys(SIFRE)
            butona_tikla_idsiz(driver)
            time.sleep(5)

        # 3. VERİYİ ÇEK
        # Tablo varsa tabloyu, yoksa body'i al
        tablolar = driver.find_elements(By.TAG_NAME, "table")
        if tablolar:
            yeni_veri = max(tablolar, key=lambda t: len(t.text)).text
        else:
            yeni_veri = driver.find_element(By.TAG_NAME, "body").text
            
        # 4. ESKİ VERİYLE KIYASLA
        eski_veri = ""
        if os.path.exists("son_durum.txt"):
            with open("son_durum.txt", "r", encoding="utf-8") as f:
                eski_veri = f.read()

        if yeni_veri != eski_veri:
            print("Değişiklik var!")
            # Sadece dosya boş değilse (ilk çalışmada bildirim atmasın diye)
            if eski_veri != "":
                telegram_gonder("🚨 GITHUB BOTU: Notlarında değişiklik tespit ettim!")
            
            # Yeni veriyi dosyaya kaydet
            with open("son_durum.txt", "w", encoding="utf-8") as f:
                f.write(yeni_veri)
        else:
            print("Değişiklik yok.")

    except Exception as e:
        print(f"Hata: {e}")
        # telegram_gonder(f"Bot hata aldı: {e}") # İstersen açabilirsin
    finally:
        driver.quit()

if __name__ == "__main__":

    main()
