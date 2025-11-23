# 🎓 Sakarya University Grade Tracker (SABIS Automation)

![Python](https://img.shields.io/badge/Python-3.9-blue?style=for-the-badge&logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-Webdriver-43B02A?style=for-the-badge&logo=selenium&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-API-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)

An automated, serverless web scraping tool designed to track university grades in real-time. It runs on a cloud-based CI/CD pipeline and delivers instant push notifications via Telegram whenever a new grade is entered into the Student Information System (OBS/SABIS).

## 🚀 Key Features

- **☁️ Serverless Architecture:** Runs entirely on **GitHub Actions** (Cron Jobs) every 15 minutes. No local server required.
- **🔐 Secure Authentication:** Handles **SSO (Single Sign-On)** and dual-login mechanisms securely using GitHub Secrets.
- **🕵️‍♂️ Smart Detection:** Compares the current state of the grade table with cached data to prevent false positives.
- **📱 Instant Alerts:** Integrates with **Telegram Bot API** for real-time mobile notifications.
- **🛡️ Headless Browser:** Utilizes Selenium in headless mode with anti-detection headers.

## 🛠️ Tech Stack

* **Core:** Python 3.x
* **Web Scraping:** Selenium WebDriver (Chrome)
* **Network:** Requests Library
* **DevOps:** GitHub Actions (Scheduled Workflows)
* **Notifications:** Telegram REST API

## ⚙️ How It Works

1.  **Trigger:** The workflow wakes up automatically every 15 minutes via Cron Schedule.
2.  **Login:** The bot authenticates with the university system using encrypted credentials.
3.  **Navigation:** It navigates through the dashboard to access the specific transcript/grades page.
4.  **Comparison:** It scrapes the DOM body and compares it with the `son_durum.txt` (last known state).
5.  **Action:**
    * *If changed:* Sends a Telegram message and commits the new state to the repo.
    * *If same:* Terminates quietly to save resources.

## 🔒 Security Note

This project uses **GitHub Secrets** to store sensitive data (Student ID, Passwords, API Tokens). No credentials are hard-coded in the source files.

---
Developed by Berkan Akten
