# Khutbah Scraper

This script scrapes khutbahs from **khutabaa.com**, translates them into multiple languages using **Google Cloud Translation**, and saves them to **Google Firestore**.
It runs continuously and adds new khutbahs automatically.

---

## Features

* Scrapes khutbah title, speaker, date, and full text
* Checks Firestore to avoid duplicates
* Translates khutbahs into several languages
* Saves original and translated data to Firestore
* Runs in a loop and checks for new khutbahs every 10 seconds

---

## Requirements

* Python 3
* Google Cloud credentials with:

  * Firestore enabled
  * Translation API enabled

Install dependencies:

```
pip install -r requirements.txt
```

Set your credentials:

```
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your-key.json"
```

---

## Run

```
python scraper.py
```
