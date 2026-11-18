
    
  
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

