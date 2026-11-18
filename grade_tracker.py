import json
import os
import time
from typing import Dict, List, Optional

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# GitHub Actions Secrets
KULLANICI_ADI = os.environ["OKUL_NO"]
SIFRE = os.environ["OKUL_SIFRE"]
TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]

# SABİS settings
LOGIN_URL = "https://sabis.sakarya.edu.tr/"
NOT_URL = "https://obs.sabis.sakarya.edu.tr/Ders"

# Login element IDs
ID_USER_1 = "UserName"
ID_PASS_1 = "Password"
ID_BTN_1 = "btnLogin"
ID_USER_2 = "Username"
ID_PASS_2 = "Password"
XPATH_BTN_2 = '//*[@id="kt_login_form"]/div[4]/button'

# The same file is committed by the existing GitHub Actions workflow.
STATE_FILE = "son_durum.txt"
STATE_FORMAT = "obs-grade-snapshot-v1"

GRADE_HEADER_KEYWORDS = (
    "not",
    "vize",
    "final",
    "butunleme",
    "basari",
    "ortalama",
    "puan",
    "sinav",
    "harf",
    "quiz",
    "odev",
    "proje",
    "sonuc",
    "durum",
)


def normalize_text(value: str) -> str:
    """Collapse whitespace and normalize Turkish characters for header matching."""
    value = " ".join((value or "").split()).strip().lower()
    translation = str.maketrans(
        {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "ö": "o",
            "ş": "s",
            "ü": "u",
        }
    )
    return value.translate(translation)


def telegram_gonder(mesaj: str) -> None:
    """Send a Telegram message and fail the workflow if Telegram rejects it."""
    response = requests.post(
        "https://api.telegram.org/bot{}/sendMessage".format(TG_TOKEN),
        data={"chat_id": TG_CHAT_ID, "text": mesaj},
        timeout=20,
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError("Telegram mesajı gönderilemedi: {}".format(result))


def butona_tikla_idsiz(driver) -> None:
    """Try alternative selectors for the second SABİS login button."""
    selectors = [
        (By.XPATH, XPATH_BTN_2),
        (By.XPATH, "//button[@type='submit']"),
        (By.XPATH, "//*[contains(text(), 'Giriş')]"),
    ]
    last_error = None
    for by, selector in selectors:
        try:
            driver.find_element(by, selector).click()
            return
        except Exception as exc:
            last_error = exc
    raise RuntimeError("İkinci giriş ekranındaki butona tıklanamadı.") from last_error


def find_grade_table_rows(driver) -> Dict[str, dict]:
    """Read course names and grade-related columns from the SABİS grade table.

    The page is inspected through its table headers instead of hashing the whole
    page. This keeps unrelated page changes from triggering grade alerts.
    """
    tables = driver.find_elements(By.TAG_NAME, "table")
    courses: Dict[str, dict] = {}

    for table in tables:
        rows = table.find_elements(By.CSS_SELECTOR, "tr")
        if len(rows) < 2:
            continue

        # Find a header row. Some pages use <thead>; others put the header in
        # the first <tr>, so inspect the first few rows for recognizable labels.
        header_index = None
        headers = []
        for row_index, row in enumerate(rows[:5]):
            cells = row.find_elements(By.CSS_SELECTOR, "th, td")
            candidate = [cell.text.strip() for cell in cells]
            normalized = [normalize_text(cell) for cell in candidate]
            has_course_header = any("ders" in item or "course" in item for item in normalized)
            has_grade_header = any(
                keyword in item
                for item in normalized
                for keyword in GRADE_HEADER_KEYWORDS
            )
            if has_course_header and has_grade_header:
                header_index = row_index
                headers = candidate
                break

        if header_index is None or not headers:
            continue

        normalized_headers = [normalize_text(header) for header in headers]

        # Prefer a course-name column over a course-code column.
        course_candidates = []
        for index, header in enumerate(normalized_headers):
            if "ders adi" in header or "course name" in header:
                course_candidates.append((3, index))
            elif header == "ders" or header == "course":
                course_candidates.append((2, index))
            elif "ders" in header or "course" in header:
                course_candidates.append((1, index))
        if not course_candidates:
            continue
        course_index = sorted(course_candidates, reverse=True)[0][1]

        code_index = None
        for index, header in enumerate(normalized_headers):
            if index != course_index and (
                "ders kodu" in header or header == "kod" or "course code" in header
            ):
                code_index = index
                break

        grade_indexes = [
            index
            for index, header in enumerate(normalized_headers)
            if index != course_index
            and index != code_index
            and any(keyword in header for keyword in GRADE_HEADER_KEYWORDS)
        ]
        if not grade_indexes:
            continue

        for row in rows[header_index + 1 :]:
            cells = row.find_elements(By.CSS_SELECTOR, "th, td")
            values = [" ".join(cell.text.split()).strip() for cell in cells]
            if len(values) <= course_index:
                continue

            course_name = values[course_index]
            if not course_name:
                continue

            course_code = ""
            if code_index is not None and len(values) > code_index:
                course_code = values[code_index]

            grade_values = {}
            for index in grade_indexes:
                if index >= len(values):
                    continue
                label = headers[index].strip() or "Not alanı {}".format(index + 1)
                grade_values[label] = values[index]

            # A course code is a more stable key if SABİS provides one.
            course_key = course_code or course_name
            unique_key = course_key
            suffix = 2
            while unique_key in courses:
                unique_key = "{}#{}".format(course_key, suffix)
                suffix += 1

            courses[unique_key] = {
                "name": course_name,
                "code": course_code,
                "grades": grade_values,
            }

    if not courses:
        raise RuntimeError(
            "SABİS sayfasında ders/not tablosu otomatik olarak bulunamadı. "
            "Giriş başarılı olsa bile tablo yapısı değişmiş veya notlar bir HTML "
            "tablosu yerine farklı bir bileşende gösteriliyor olabilir."
        )

    return courses


def load_old_snapshot() -> Optional[dict]:
    """Load the structured snapshot; return None for the old MD5-only format."""
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        # The previous version stored only an MD5 hash in this file.
        return None

    if not isinstance(data, dict) or data.get("format") != STATE_FORMAT:
        return None
    if not isinstance(data.get("courses"), dict):
        return None
    return data


def save_snapshot(courses: Dict[str, dict]) -> None:
    snapshot = {"format": STATE_FORMAT, "courses": courses}
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(snapshot, file, ensure_ascii=False, indent=2)
        file.write("\n")


def make_course_message(old_course: Optional[dict], new_course: dict) -> str:
    course_name = new_course.get("name", "Bilinmeyen ders")
    old_grades = (old_course or {}).get("grades", {})
    new_grades = new_course.get("grades", {})

    if old_course is None:
        lines = [
            "🆕 Yeni ders/not kaydı",
            "📚 Ders: {}".format(course_name),
            "📝 Not bilgileri:",
        ]
        for label, value in new_grades.items():
            if value:
                lines.append("• {}: {}".format(label, value))
        if len(lines) == 3:
            lines.append("• Henüz not bilgisi girilmemiş.")
        return "\n".join(lines)

    changed_fields = []
    all_labels = list(dict.fromkeys(list(old_grades.keys()) + list(new_grades.keys())))
    for label in all_labels:
        old_value = old_grades.get(label, "")
        new_value = new_grades.get(label, "")
        if old_value != new_value:
            old_display = old_value if old_value else "—"
            new_display = new_value if new_value else "—"
            changed_fields.append("• {}: {} → {}".format(label, old_display, new_display))

    if not changed_fields:
        return ""

    return "\n".join(
        [
            "🚨 SABİS NOT GÜNCELLEMESİ",
            "📚 Ders: {}".format(course_name),
            "📝 Değişen notlar:",
        ]
        + changed_fields
    )


def find_changes(old_snapshot: Optional[dict], new_courses: Dict[str, dict]) -> List[str]:
    # The old version stored a single MD5 hash, so it cannot tell us which
    # course changed. The first run with this version only creates a baseline.
    if old_snapshot is None:
        print("İlk yapılandırılmış kayıt oluşturuluyor; bu çalışmada bildirim gönderilmeyecek.")
        return []

    old_courses = old_snapshot.get("courses", {})
    messages = []

    for course_key, new_course in new_courses.items():
        old_course = old_courses.get(course_key)
        message = make_course_message(old_course, new_course)
        if message:
            messages.append(message)

    return messages


def send_messages_in_chunks(messages: List[str]) -> None:
    if not messages:
        return

    header = "🎓 OBS NOT TAKİP BİLDİRİMİ\n\n"
    current = header
    for message in messages:
        addition = message + "\n\n"
        if len(current) + len(addition) > 3800 and current != header:
            telegram_gonder(current.rstrip())
            current = header
        current += addition

    if current != header:
        telegram_gonder(current.rstrip())


def main() -> None:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        print("SABİS'e giriş yapılıyor...")
        driver.get(LOGIN_URL)
        time.sleep(3)
        driver.find_element(By.ID, ID_USER_1).send_keys(KULLANICI_ADI)
        driver.find_element(By.ID, ID_PASS_1).send_keys(SIFRE)
        driver.find_element(By.ID, ID_BTN_1).click()
        time.sleep(5)

        print("Not sayfası açılıyor...")
        driver.get(NOT_URL)
        time.sleep(5)

        if driver.find_elements(By.ID, ID_USER_2):
            print("İkinci giriş ekranı tamamlanıyor...")
            driver.find_element(By.ID, ID_USER_2).send_keys(KULLANICI_ADI)
            driver.find_element(By.ID, ID_PASS_2).send_keys(SIFRE)
            butona_tikla_idsiz(driver)
            time.sleep(5)

        time.sleep(3)
        new_courses = find_grade_table_rows(driver)
        old_snapshot = load_old_snapshot()
        messages = find_changes(old_snapshot, new_courses)

        # Send first. If Telegram fails, do not update the stored snapshot;
        # the next scheduled run can retry the notification.
        send_messages_in_chunks(messages)
        save_snapshot(new_courses)

        if messages:
            print("{} ders için değişiklik bildirimi gönderildi.".format(len(messages)))
        else:
            print("Not değişikliği yok veya ilk kayıt oluşturuldu.")

    except Exception as exc:
        print("Hata oluştu: {}".format(exc))
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
