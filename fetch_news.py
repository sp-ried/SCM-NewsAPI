
# fetch_news.py
import os
import requests
from datetime import datetime
from keywords import KEYWORDS

API_URL = "https://api.currentsapi.services/v1/search"
API_KEY = os.environ.get("CURRENTS_API_KEY")
OUTPUT_FILE = "news.md"
MAX_PER_KEYWORD = 10  # halte es knapp

def fetch_for_keyword(keyword: str):
    params = {
        "keywords": keyword,
        "language": "en",  # bei Bedarf "de" probieren; CurrentsAPI ist primär englisch
        "limit": MAX_PER_KEYWORD,
    }
    headers = {"Accept": "application/json"}
    r = requests.get(API_URL, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get("news", [])

def main():
    if not API_KEY:
        raise RuntimeError("Fehlender API Key: Bitte GitHub Secret CURRENTS_API_KEY setzen.")

    # CurrentsAPI erwartet apiKey als Query-Parameter, also hängen wir ihn direkt an die URL an.
    # (Alternativ könnte man ihn in params setzen; hier ist es explizit)
    global API_URL
    API_URL = f"{API_URL}?apiKey={API_KEY}"

    lines = []
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"# News-Übersicht\n\n*Stand: {now}*\n")
    lines.append("| Keyword | Headline | Link |\n|---|---|---|")

    for kw in KEYWORDS:
        try:
            items = fetch_for_keyword(kw)
            if not items:
                lines.append(f"| {kw} | *(keine Treffer)* | -*- |")
                continue
            for n in items:
                title = (n.get("title") or "").replace("|", " ")
                link = n.get("url") or ""
                lines.append(f"| {kw} | {title} | {link} |")
        except Exception as e:
            lines.append(f"| {kw} | **Fehler:** {e} | -*- |")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

if __name__ ==if __name__ == "__main__":
