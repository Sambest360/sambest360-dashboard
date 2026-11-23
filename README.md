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

## Instagram (@samuelplayz360_ig)
Instagram has no public listing the refresh can read, so Reels are listed in `instagram-links.json` (`reels`: `{link,title,game,date,time}`). `refresh.py` upserts each one as a "Reel" item (idempotent, keyed by reel shortcode) and reads likes/comments per Reel anonymously with yt-dlp. Views and follower counts are not public to anonymous readers, so they show `n/a` (never estimated). No cookies or logins are used. **To add a new Reel, append it to `instagram-links.json` and push**; the next daily refresh (or a manual run) shows it.
