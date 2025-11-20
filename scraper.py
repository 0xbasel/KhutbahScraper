import time
import requests
from bs4 import BeautifulSoup
import re
import uuid
import html
from google.cloud import translate_v2 as translate
from google.cloud import firestore
import firebase_admin
from google.cloud.firestore_v1 import FieldFilter

"""
Set GOOGLE_APPLICATION_CREDENTIALS environment variable
 Before running this script.
"""

firebase_admin.initialize_app()
db = firestore.Client()

translate_client = translate.Client()

TARGET_LANGUAGES = {
    "english": "en",
    "indonesian": "id",
    "urdu": "ur",
    "bengali": "bn",
    "turkish": "tr",
    "farsi": "fa",
    "hausa": "ha",
    "pashto": "ps",
    "malay": "ms",
    "french": "fr",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def translate_text(text, target):
    """Translate Arabic text to target language."""
    if not text.strip():
        return ""
    lines = text.split("\n")
    translated_lines = []
    for line in lines:
        if not line.strip():
            translated_lines.append("")
            continue
        result = translate_client.translate(line, target_language=target, source_language="ar")
        translated_lines.append(result["translatedText"])
    return "\n".join(translated_lines)


def scrape_khutbah(url):
    """Scrape a single khutbah page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Failed to fetch khutbah {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    title_tag = soup.find("h1", id="title")
    speaker_tag = soup.find("a", id="author-name")
    date_tag = soup.find("span", id="date")
    body_tag = soup.find("div", id="body")

    if not all([title_tag, speaker_tag, date_tag, body_tag]):
        return None

    title = title_tag.get_text(strip=True)
    speaker = speaker_tag.get_text(strip=True)
    date_text = date_tag.get_text(" ", strip=True)
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", date_text)
    gregorian_date = date_match.group(0) if date_match else "1970-01-01"
    khutbah_text = body_tag.get_text()

    return {
        "title": title,
        "speaker": speaker,
        "date": gregorian_date,
        "mosque": "",  # fill this later
        "text": khutbah_text,
    }


def scrape_khutbahs(main_url):
    """Get all khutbah URLs from the main page."""
    try:
        resp = requests.get(main_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Failed to fetch main page: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("table#table2 a.article-title")
    return [a["href"] for a in articles if a.get("href")]


def khutbah_exists(title):
    """Check if a khutbah already exists in Firestore."""
    ref = db.collection("khutbahs").where(
        filter=FieldFilter("title", "==", title)
    ).limit(1).get()
    return len(ref) > 0


def save_khutbah_to_firestore(khutbah):
    """Save khutbah and translations to Firestore."""
    khutbah_id = str(uuid.uuid4())
    translations = {}
    for lang_name, lang_code in TARGET_LANGUAGES.items():
        translations[lang_code] = {
            "title": html.unescape(translate_text(khutbah["title"], lang_code)),
            "text": html.unescape(translate_text(khutbah["text"], lang_code)),
        }
        print(f"Saved translation: {lang_name}")

    doc_data = {
        "id": khutbah_id,
        "title": khutbah["title"],
        "text": khutbah["text"],
        "translations": translations,
        "mosque": khutbah["mosque"],
        "date": khutbah["date"],
        "speaker": khutbah["speaker"],
    }
    db.collection("khutbahs").document(khutbah_id).set(doc_data)
    print(f"🔥 Added new khutbah: {khutbah['title']}")


if __name__ == "__main__":
    MAIN_URL = "https://khutabaa.com/ar/khutub/haramyn"

    while True:
        print("\n⏳ Running scraper...")
        khutbah_urls = scrape_khutbahs(MAIN_URL)

        if not khutbah_urls:
            print("⚠️ No khutbahs found. Retrying in 10 seconds...")
            time.sleep(10)
            continue

        for url in khutbah_urls:
            khutbah = scrape_khutbah(url)
            if not khutbah:
                continue

            print(f"\nChecking: {khutbah['title']}")
            if khutbah_exists(khutbah["title"]):
                print("⏹ Khutbah already exists. Skipping this one.")
                continue

            save_khutbah_to_firestore(khutbah)

        print("✅ Batch finished. Waiting 10 seconds...\n")
        time.sleep(10)
