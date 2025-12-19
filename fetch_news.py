
# fetch_news.py
import os
import time
import requests
from datetime import datetime, timedelta
from keywords import KEYWORDS

API_BASE = "https://api.currentsapi.services/v1/search"
API_KEY = os.environ.get("CURRENTS_API_KEY")
OUTPUT_FILE = "news.md"

# Performance/Rate-Limit: klein starten
MAX_PER_KEYWORD = 8
LANGUAGE = "en"  # optional: "de"
# Optional: Tagesfilter (heute). CurrentsAPI unterstützt 'start_date'/'end_date' im ISO-Format (YYYY-MM-DD).
USE_TODAY_WINDOW = True

# Timeouts (connect, read)
TIMEOUT = (10, 30)  # 10s Verbindungsaufbau, 30s Antwort lesen

# Retry-Strategie
MAX_RETRIES = 3
BACKOFF_BASE_SEC = 2  # exponentiell: 2s, 4s, 8s

def fetch_with_retry(session: requests.Session, api_url: str, keyword: str):
    params = {
        "keywords": keyword,
        "language": LANGUAGE,
        "limit": MAX_PER_KEYWORD,
    }
    if USE_TODAY_WINDOW:
        # Filter auf heutiges Datum (UTC-basiert)
        today = datetime.utcnow().date()
        params["start_date"] = today.isoformat()
        params["end_date"] = today.isoformat()

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(api_url, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
            return data.get("news", [])
        except requests.Timeout as e:
            last_err = e
        except requests.RequestException as e:
            last_err = e

        # Backoff (nur wenn weiterer Versuch folgt)
        if attempt < MAX_RETRIES:
            sleep_sec = BACKOFF_BASE_SEC ** attempt  # 2, 4, 8
            time.sleep(sleep_sec)

    # Nach allen Versuchen: Fehler zurückgeben
    raise last_err if last_err else RuntimeError("Unbekannter Fehler")

def main():
    lines = []
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"# News-Übersicht\n\n*Stand: {now}*\n")
    lines.append("| Keyword | Headline | Link |\n|---|---|---|")

    if not API_KEY:
        lines.append("| -*- | **Fehler:** Secret CURRENTS_API_KEY fehlt | -*- |")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return

    api_url = f"{API_BASE}?apiKey={API_KEY}"

    # Session für Reuse + Header
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "User-Agent": "SCM-NewsFetcher/1.0 (+github actions)"
    })

    for kw in KEYWORDS:
        try:
            items = fetch_with_retry(session, api_url, kw)
            if not items:
                lines.append(f"| {kw} | *(keine Treffer heute)* | -*- |")
                continue

            # Kompakt: nur Titel+Link; Sonderzeichen im Titel entschärfen
            for n in items:
                title = (n.get("title") or "").replace("|", " ")
                link = n.get("url") or ""
                lines.append(f"| {kw} | {title} | {link} |")

        except requests.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            msg = e.response.text[:160].replace("\n", " ") if e.response and e.response.text else str(e)
            lines.append(f"| {kw} | **HTTP {status}:** {msg} | -*- |")
        except requests.Timeout:
            lines.append(f"| {kw} | **Zeitüberschreitung** nach {TIMEOUT[1]}s | -*- |")
        except Exception as e:
            lines.append(f"| {kw} | **Fehler:** {e} | -*- |")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
