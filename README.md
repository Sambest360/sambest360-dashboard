# samBest360 Accounts Dashboard
Static site: `index.html` + `data.json` (Chart.js from CDN). No build step.

## Daily auto-refresh (no box, no bots needed)
`.github/workflows/refresh.yml` runs every day at 04:00 UTC (06:00 SAST) and on demand
(Actions tab -> Daily refresh -> Run workflow). It runs `python refresh.py` (yt-dlp pulls public
YouTube / Twitch / TikTok stats), appends today's row to `snapshots.jsonl`, commits `data.json` +
`snapshots.jsonl`, and Vercel's Git integration redeploys the site.

## Files
- `refresh.py` live pull + merge (idempotent; a failing platform is skipped and shown as "last attempt failed").
- `seed.json` / `build_data.py` / `attention.json`: one-off xlsx history seed (run only on the box with the roundup xlsx: `python3 build_data.py && python3 refresh.py`).
- `attention.json` is edited by hand for the "Needs attention" panel (edit, then also copy the items into `data.json` -> `attention`).

## Manual refresh
`pip install yt-dlp && python3 refresh.py && git add -A && git commit -m refresh && git push`
