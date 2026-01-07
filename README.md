# Discord Webhook - Recruit (Python)

Job postings from INTHISWORK (IT 개발 검색 결과) are crawled with Playwright, filtered by a zero-shot classifier, and posted to Discord via webhook.

## How it works
- Loads `AID_DISCORD_WEBHOOK_URL` from `.env`.
- Reads `data/homepage.json` (list of pages + `latestPostIndex`).
- Playwright (Chromium) loads each page, grabs up to 10 links (`.fusion-image-wrapper a`), and keeps only posts newer than `latestPostIndex`.
- Zero-shot classification (AI/RESEARCH/DATA) filters out non-AI posts and ones containing "경력".
- Builds a Discord message and sends it; updates `latestPostIndex` on success.

## Run locally
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium
echo "AID_DISCORD_WEBHOOK_URL=your_webhook" > .env
python main.py
```

## GitHub Actions
- `.github/workflows/schedule.yml` runs daily Mon–Sat at 11:00 UTC (20:00 KST) and on `workflow_dispatch`.
- Steps: checkout, install Python deps, `playwright install --with-deps chromium`, create `.env`, run `python main.py`, commit updated `data/homepage.json`.

## Data file
`data/homepage.json`
```json
{
  "data": [
    { "url": "https://inthiswork.com/?s=IT%EA%B0%9C%EB%B0%9C", "homepage": "INTHISWORK" }
  ],
  "latestPostIndex": 245656
}
```
Only edit the `data` array to add/remove sources; `latestPostIndex` is maintained by the crawler.
