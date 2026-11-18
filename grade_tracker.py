import json
import os
import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

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

# SABİS /Ders page: each course is rendered as a separate card.
COURSE_CARD_SELECTOR = "div.card.card-custom.card-stretch"
COURSE_CODE_SELECTOR = ".symbol-label"
COURSE_NAME_SELECTOR = "a.font-size-h5, a.text-dark.font-weight-bolder"
COURSE_TABLE_SELECTOR = "table.table"

# The same file is committed by the existing GitHub Actions workflow.
STATE_FILE = "son_durum.txt"
STATE_FORMAT = "obs-grade-snapshot-v2"


def normalize_text(value: str) -> str:
    """Collapse whitespace and normalize Turkish characters for comparisons."""
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


def element_text(parent, selector: str) -> str:
    """Return an element's normalized visible text, or an empty string."""
    elements = parent.find_elements(By.CSS_SELECTOR, selector)
    if not elements:
        return ""
    return " ".join(elements[0].text.split()).strip()


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
    """Read grades from the individual course cards on SABİS /Ders.

    Actual page structure (confirmed from the supplied HTML):
      card -> .symbol-label (course code)
           -> a.font-size-h5 (course name)
           -> table.table -> tbody tr -> td[ratio, assessment type, grade]

    Duplicate assessment types are distinguished by their weight and occurrence
    number, e.g. 'Proje / Tasarım (%7,2) #2'. Blank grades are deliberately
    retained so a later blank-to-grade transition is detected.
    """
    cards = driver.find_elements(By.CSS_SELECTOR, COURSE_CARD_SELECTOR)
    courses: Dict[str, dict] = {}

    for card in cards:
        course_code = element_text(card, COURSE_CODE_SELECTOR)
        course_name = element_text(card, COURSE_NAME_SELECTOR)
        if not course_code and not course_name:
            continue

        tables = card.find_elements(By.CSS_SELECTOR, COURSE_TABLE_SELECTOR)
        if not tables:
            # Ignore unrelated cards that happen to share some CSS classes.
            continue

        table = tables[0]
        rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
        if not rows:
            # A fallback for a table whose rows are not wrapped in <tbody>.
            rows = table.find_elements(By.CSS_SELECTOR, "tr")

        parsed_rows = []
        for row in rows:
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            if len(cells) < 3:
                continue

            ratio = " ".join(cells[0].text.split()).strip()
            assessment_type = " ".join(cells[1].text.split()).strip()
            grade = " ".join(cells[2].text.split()).strip()
            if not assessment_type:
                continue

            parsed_rows.append(
                {
                    "ratio": ratio,
                    "assessment_type": assessment_type,
                    "grade": grade,
                }
            )

        if not parsed_rows:
            # A course card without assessable rows is not useful for tracking.
            continue

        # Count identical (assessment type, ratio) rows first. This makes labels
        # unambiguous when a course has several projects/homeworks with same weight.
        totals = Counter(
            (normalize_text(item["assessment_type"]), normalize_text(item["ratio"]))
            for item in parsed_rows
        )
        occurrences = defaultdict(int)
        grade_values = {}

        for item in parsed_rows:
            assessment_type = item["assessment_type"]
            ratio = item["ratio"]
            identity = (normalize_text(assessment_type), normalize_text(ratio))
            occurrences[identity] += 1

            label = assessment_type
            if ratio:
                label += " (%{})".format(ratio)
            if totals[identity] > 1:
                label += " #{}".format(occurrences[identity])

            grade_values[label] = item["grade"]

        # Course code remains the stable identity across runs. Course name is
        # used as a fallback in case the page omits the code.
        course_key = course_code or course_name
        unique_key = course_key
        suffix = 2
        while unique_key in courses:
            unique_key = "{}#{}".format(course_key, suffix)
            suffix += 1

        courses[unique_key] = {
            "name": course_name or course_code or "Bilinmeyen ders",
            "code": course_code,
            "grades": grade_values,
        }

    if not courses:
        raise RuntimeError(
            "SABİS girişinden sonra ders kartları okunamadı. "
            "Beklenen kart seçicisi: '{}'. Sayfa URL: {}. "
            "Girişin tamamlandığını ve /Ders sayfasının açıldığını kontrol edin."
            .format(COURSE_CARD_SELECTOR, driver.current_url)
        )

    print("{} ders kartı ve not satırları okundu.".format(len(courses)))
    return courses


def load_old_snapshot() -> Optional[dict]:
    """Load structured state; return None for old MD5 / older JSON formats."""
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        # Earlier versions stored only an MD5 hash or a different state format.
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
    course_code = new_course.get("code", "")
    old_grades = (old_course or {}).get("grades", {})
    new_grades = new_course.get("grades", {})

    course_lines = ["📚 Ders: {}".format(course_name)]
    if course_code:
        course_lines.append("🔖 Kod: {}".format(course_code))

    if old_course is None:
        lines = ["🆕 Yeni ders kaydı"] + course_lines + ["📝 Mevcut not bilgileri:"]
        for label, value in new_grades.items():
            if value:
                lines.append("• {}: {}".format(label, value))
        if len(lines) == len(course_lines) + 2:
            lines.append("• Henüz not girilmemiş.")
        return "\n".join(lines)

    changed_fields = []
    all_labels = list(dict.fromkeys(list(old_grades.keys()) + list(new_grades.keys())))
    for label in all_labels:
        old_value = old_grades.get(label, "")
        new_value = new_grades.get(label, "")
        if old_value != new_value:
            old_display = old_value if old_value else "—"
            new_display = new_value if new_value else "—"
            changed_fields.append(
                "• {}: {} → {}".format(label, old_display, new_display)
            )

    if not changed_fields:
        return ""

    return "\n".join(
        ["🚨 SABİS NOT GÜNCELLEMESİ"] + course_lines + ["📝 Değişen notlar:"] + changed_fields
    )


def find_changes(old_snapshot: Optional[dict], new_courses: Dict[str, dict]) -> List[str]:
    # Old MD5-only / older JSON snapshots cannot identify individual grades.
    # The first run with this format creates a baseline without a mass alert.
    if old_snapshot is None:
        print(
            "İlk yeni formatlı kayıt oluşturuluyor; bu çalışmada bildirim gönderilmeyecek."
        )
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
        time.sleep(3)

        if driver.find_elements(By.ID, ID_USER_2):
            print("İkinci giriş ekranı tamamlanıyor...")
            driver.find_element(By.ID, ID_USER_2).send_keys(KULLANICI_ADI)
            driver.find_element(By.ID, ID_PASS_2).send_keys(SIFRE)
            butona_tikla_idsiz(driver)
            time.sleep(5)

        # Wait for SABİS to finish rendering its course cards before parsing.
        WebDriverWait(driver, 20).until(
            lambda current_driver: current_driver.find_elements(
                By.CSS_SELECTOR, COURSE_CARD_SELECTOR
            )
        )

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
