
# fetch_news.py
import os
import time
import requests
from datetime import datetime
from keywords import KEYWORDS

API_BASE = "https://api.currentsapi.services/v1/search"
API_KEY = os.environ.get("CURRENTS_API_KEY")

OUTPUT_FILE = "news.md"
DEBUG_LOG = "news_debug.log"

# Abfrage-Parameter
LANGUAGE = "de"          # Deutsch bevorzugt
MAX_PER_KEYWORD = 8      # schlank halten
TIMEOUT = (10, 30)       # (connect=10s, read=30s)
MAX_RETRIES = 3
BACKOFF_BASE_SEC = 2      # 2s, 4s, 8s
DELAY_BETWEEN_CALLS = 1.0 # 1s zwischen Keywords (sequentiell)

def prepare_url(session: requests.Session, api_url: str, params: dict) -> str:
    """Baut die finale GET-URL (für Debug-Ausgaben)."""
    req = requests.Request("GET", api_url, params=params)
    prepped = session.prepare_request(req)
    return prepped.url

def fetch_with_retry(session: requests.Session, api_url: str, params: dict):
    """GET mit Retries/Backoff und JSON-Decode."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(api_url, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
            return r, data
        except (requests.Timeout, requests.RequestException) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE_SEC ** attempt)
    raise last_err if last_err else RuntimeError("Unbekannter Fehler")

def main():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Markdown-Output vorbereiten
    lines = []
    lines.append(f"# News-Übersicht\n\n*Stand: {now}*\n")
    lines.append("| Keyword | Headline | Link |\n|---|---|---|")

    # Debug-Log vorbereiten
    debug_lines = []
    debug_lines.append(f"[INFO] Zeit: {now}")
    debug_lines.append(f"[INFO] KEYWORDS: {', '.join(KEYWORDS)}")
    debug_lines.append(f"[INFO] Sprache: {LANGUAGE}, Limit pro Keyword: {MAX_PER_KEYWORD}")

    if not API_KEY:
        msg = "Secret CURRENTS_API_KEY fehlt"
        lines.append(f"| -*- | **Fehler:** {msg} | -*- |")
        debug_lines.append(f"[ERROR] {msg}")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        with open(DEBUG_LOG, "w", encoding="utf-8") as f:
            f.write("\n".join(debug_lines))
        return

    # API-URL mit apiKey als Query (wie in den offiziellen Beispielen)
    api_url = f"{API_BASE}?apiKey={API_KEY}"

    # Session für HTTP-Reuse und sauberen UA
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "User-Agent": "SCM-NewsFetcher/1.1 (+github actions)"
    })

    # Pro Keyword: eigene, sequenzielle Anfrage
    for kw in KEYWORDS:
        params = {
            "keywords": kw,
            "language": LANGUAGE,
            "limit": MAX_PER_KEYWORD,
        }

        full_url = prepare_url(session, api_url, params)
        print(f"[DEBUG] GET {full_url}")
        debug_lines.append(f"[DEBUG] GET {full_url}")

        try:
            resp, data = fetch_with_retry(session, api_url, params)
            items = data.get("news", []) or []

            debug_lines.append(f"[OK] {kw}: status={resp.status_code}, items={len(items)}")

            if not items:
                lines.append(f"| {kw} | *(keine Treffer heute)* | -*- |")
            else:
                for n in items:
                    title = (n.get("title") or "").replace("|", " ")
                    link = n.get("url") or ""
                    lines.append(f"| {kw} | {title} | {link} |")

        except requests.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            body = e.response.text[:200].replace("\n", " ") if e.response and e.response.text else str(e)
            lines.append(f"| {kw} | **HTTP {status}:** {body} | -*- |")
            debug_lines.append(f"[HTTP-ERROR] {kw}: status={status}, body={body}")
        except requests.Timeout:
            lines.append(f"| {kw} | **Zeitüberschreitung** nach {TIMEOUT[1]}s | -*- |")
            debug_lines.append(f"[TIMEOUT] {kw}: nach {TIMEOUT[1]}s")
        except Exception as e:
            lines.append(f"| {kw} | **Fehler:** {e} | -*- |")
            debug_lines.append(f"[ERROR] {kw}: {e}")

        # Sequentielle Abfragen sicherstellen
        time.sleep(DELAY_BETWEEN_CALLS)


    # Dateien schreiben
    with open    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    with open(DEBUG_LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(debug_lines))


if __name__ == "__main__":
