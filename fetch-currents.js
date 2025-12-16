// fetch-currents
// Zweck: Headlines von CurrentsAPI nach Keywords holen und als Markdownliste ausgeben.
// Voraussetzungen: Node.js >= 18. Optional: dotenv für .env-Unterstützung.

import fs from 'node:fs';
import path from 'node:path';

try {
  // Optional .env laden (falls installiert)
  const useDotenv = (() => {
    try { return (await import('dotenv')).config(); } catch { return null; }
  })();

  const API_KEY = process.env.CURRENTS_API_KEY;
  if (!API_KEY) {
    console.error('Fehler: CURRENTS_API_KEY fehlt (setze ihn in .env oder als Environment Variable).');
    process.exit(1);
  }

  // ---- KONFIG ----
  // STARTE mit einem Keyword; erweitern auf bis zu 20 ist simpel (Array unten).
  const KEYWORDS = [
    // ZUERST: Ein Keyword
    'Lieferkette',
    // Später einfach ergänzen: bis zu 20
    // 'Tesla', 'Logistik', 'KI', 'Nachhaltigkeit', ...
  ];

  // Sprache für die Ergebnisse (z. B. 'de' oder 'en')
  const LANGUAGE = process.env.LANGUAGE || 'de';

  // Max. Anzahl Headlines pro Keyword
  const MAX_PER_KEYWORD = Number(process.env.MAX_PER_KEYWORD || 10);

  // Optional: Duplikate über Keywords hinweg entfernen (gleicher URL)
  const dedupeAcrossKeywords = true;

  // ---- HILFSFUNKTIONEN ----
  const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

  // Sequential fetch, um Rate Limits zu schonen.
  async function fetchForKeyword(keyword) {
    const base = 'https://api.currentsapi.services/v1/search';
    const params = new URLSearchParams({
      keywords: keyword,
      language: LANGUAGE,
      page_size: String(MAX_PER_KEYWORD), // Begrenze pro Keyword
    });

    const url = `${base}?${params.toString()}`;
    const resp = await fetch(url, {
      headers: {
        // Empfohlen: Authorization-Header mit API-Key
        Authorization: API_KEY,
        // Alternativ (nicht nötig, wenn Authorization gesetzt): url += '&apiKey=...'
      },
    });

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status} für Keyword "${keyword}"`);
    }

    const data = await resp.json();
    if (data.status !== 'ok' || !Array.isArray(data.news)) {
      throw new Error(`Unerwartete API-Antwort für "${keyword}": ${JSON.stringify(data).slice(0, 200)}...`);
    }

    // Mappe relevante Felder und schneide auf MAX_PER_KEYWORD
    const items = data.news.slice(0, MAX_PER_KEYWORD).map((n) => ({
      title: n.title,
      url: n.url,
      published: n.published,
      sourceLang: n.language,
    }));

    return items;
  }

  // ---- HAUPTLOGIK ----
  // Sortiere Keywords alphabetisch (case-insensitive)
  const sortedKeywords = [...KEYWORDS].sort((a, b) =>
    a.localeCompare(b, undefined, { sensitivity: 'base' })
  );

  const seenUrls = new Set();
  const resultMap = {};

  for (const kw of sortedKeywords) {
    try {
      const items = await fetchForKeyword(kw);
      const cleaned = items.filter((it) => {
        if (!dedupeAcrossKeywords) return true;
        if (seenUrls.has(it.url)) return false;
        seenUrls.add(it.url);
        return true;
      });

      resultMap[kw] = cleaned;
      // Mini-Pause zwischen Anfragen
      await sleep(250);
    } catch (err) {
      console.error(`Fehler bei Keyword "${kw}": ${err.message}`);
      resultMap[kw] = [];
    }
  }

  // ---- AUSGABE als Markdown ----
  let md = `# CurrentsAPI Headlines nach Keywords\n\n`;
  md += `*Sprache:* \`${LANGUAGE}\`  •  *max. pro Keyword:* \`${MAX_PER_KEYWORD}\`\n\n`;

  for (const kw of sortedKeywords) {
    md += `## ${kw}\n`;
    const list = resultMap[kw];
    if (!list || list.length === 0) {
      md += `*(Keine Treffer)*\n\n`;
      continue;
    }
    for (const item of list) {
      const safeTitle = (item.title || '').replace(/\s+/g, ' ').trim();
      md += `- ${safeTitle}\n`;
    }
    md += `\n`;
  }

  // Schreibe zusätzlich in eine Datei (optional)
  const outFile = path.join(process.cwd(), 'news.md');
  fs.writeFileSync(outFile, md, 'utf-8');

  // Und drucke auf die Konsole
  console.log(md);
  console.error(`\n✅ Fertig. Markdown gespeichert in: ${outFile}`);
} catch (fatal) {
  console.error('Fataler Fehler:', fatal);
   process.exit(1);
