#!/usr/bin/env python3
"""Daily refresh: pull public stats with yt-dlp, merge into data.json, append snapshots.jsonl.
Idempotent (same-day re-run replaces that day's snapshot). One platform failing never fails the build.
Needs only: python3 + yt-dlp (pip install yt-dlp). No secrets."""
import shutil, json, re, subprocess, sys, os, datetime as dt, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
TZ = dt.timezone(dt.timedelta(hours=2))  # SAST
now = dt.datetime.now(TZ); today = now.strftime("%Y-%m-%d"); stamp = now.strftime("%Y-%m-%d %H:%M")
data = json.load(open("data.json"))
data.setdefault("refreshed", {})
def key(link):
    if not link: return None
    m = re.search(r"(?:youtu\.be/|shorts/|v=)([\w-]{11})", link)
    if m: return "yt:" + m.group(1)
    m = re.search(r"tiktok\.com/.*/video/(\d+)", link)
    if m: return "tt:" + m.group(1)
    m = re.search(r"twitch\.tv/videos/v?(\d+)", link)
    if m: return "tw:" + m.group(1)
idx = {key(i["link"]): i for i in data["items"] if key(i.get("link"))}
def ytdlp(url, extra=()):
    r = subprocess.run(([shutil.which("yt-dlp")] if shutil.which("yt-dlp") else [sys.executable, "-m", "yt_dlp"]) + [ "-j", "--skip-download", "--no-warnings", *extra, url], capture_output=True, text=True, timeout=1500)
    out = [json.loads(l) for l in r.stdout.splitlines() if l.startswith("{")]
    if not out: raise RuntimeError((r.stderr or "no output").strip()[-300:])
    return out
def game_of(t):
    t = t.lower()
    for k, g in (("gta", "GTA 6"), ("fc26", "EA FC 26"), ("fc 26", "EA FC 26"), ("helldivers", "Helldivers 2"), ("mafia", "Mafia: The Old Country"), ("poppy", "Poppy Playtime Ch2")):
        if k in t: return g
    return "Other"
def when(ts):
    d = dt.datetime.fromtimestamp(ts, TZ); return d.strftime("%Y-%m-%d"), d.strftime("%H:%M")
def upsert(k, **f):
    it = idx.get(k)
    if it:
        for a in ("views", "likes", "comments"):
            if f.get(a) is not None: it[a] = f[a]
        it["live"] = True
    else:
        it = {"comments": None, "likes": None, **f}; data["items"].append(it); idx[k] = it
snap = {"date": today, "asof": stamp}
def yt():
    ents = {}
    for tab in ("videos", "shorts"):
        for d in ytdlp(f"https://www.youtube.com/@SamuelPlayz360/{tab}"):
            ents[d["id"]] = (d, tab)
    for vid, (d, tab) in ents.items():
        dd, tm = when(d["timestamp"]) if d.get("timestamp") else (today, "")
        short = tab == "shorts" or (d.get("duration") or 999) <= 180
        upsert("yt:" + vid, title=d["title"].replace(" #Shorts", ""), platform="YouTube", date=dd, time=tm, game=game_of(d["title"]),
               type="Short" if short else "Long-form", live=True, views=d.get("view_count") or 0, likes=d.get("like_count"), comments=d.get("comment_count"),
               link=d["webpage_url"], kind="short" if short else "long-form")
    f = next((d.get("channel_follower_count") for d, _ in ents.values() if d.get("channel_follower_count") is not None), None)
    its = [i for i in data["items"] if i["platform"] == "YouTube" and i["live"]]
    snap["YouTube"] = dict(followers=f, views=sum(i["views"] for i in its), likes=sum(i["likes"] or 0 for i in its), posts=len(its))
def tt():
    ds = ytdlp("https://www.tiktok.com/@sambest360")
    for d in ds:
        dd, tm = when(d["timestamp"]) if d.get("timestamp") else (today, "")
        upsert("tt:" + d["id"], title=d.get("title") or d["id"], platform="TikTok", date=dd, time=tm, game=game_of(d.get("title") or ""),
               type="Other", live=True, views=d.get("view_count") or 0, likes=d.get("like_count"), comments=d.get("comment_count"), link=d["webpage_url"], kind="short")
    its = [i for i in data["items"] if i["platform"] == "TikTok" and i["live"]]
    snap["TikTok"] = dict(followers=None, views=sum(i["views"] for i in its), likes=sum(i["likes"] or 0 for i in its), posts=len(its))
def tw():
    pl = ytdlp("https://www.twitch.tv/sambest360/videos?filter=archives&sort=time", ("--flat-playlist",))
    ents = pl[0].get("entries") if pl and "entries" in pl[0] else pl
    for d in ents:
        vid = str(d["id"]).lstrip("v"); old = idx.get("tw:" + vid)
        dur = d.get("duration") or 0; h, r = divmod(int(dur), 3600)
        upsert("tw:" + vid, title=f'{d.get("title") or "Stream"} stream ({h}:{r//60:02d}:{r%60:02d})', platform="Twitch", date=today, time="", game=d.get("title") or "Other",
               type="Stream VOD", live=True, views=d.get("view_count") or 0, link=d["url"], kind="vod")
        if not old:
            try: dd, tm = when(ytdlp(d["url"])[0]["timestamp"]); idx["tw:" + vid].update(date=dd, time=tm)
            except Exception: pass
    f = None
    try: f = int(urllib.request.urlopen(urllib.request.Request("https://decapi.me/twitch/followcount/sambest360", headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read().decode().strip())
    except Exception: pass
    its = [i for i in data["items"] if i["platform"] == "Twitch"]
    snap["Twitch"] = dict(followers=f, views=sum(i["views"] for i in its), likes=None, posts=len(its))
for name, fn in (("YouTube", yt), ("TikTok", tt), ("Twitch", tw)):
    try:
        fn(); data["refreshed"][name] = dict(at=stamp, ok=True); print(name, "ok", snap.get(name))
    except Exception as e:
        prev = data["refreshed"].get(name, {})
        data["refreshed"][name] = dict(at=prev.get("at"), ok=False, error=str(e)[:200], attempted=stamp); print(name, "FAILED", e, file=sys.stderr)
lines = [json.loads(l) for l in open("snapshots.jsonl")] if os.path.exists("snapshots.jsonl") else []
prev_today = next((l for l in lines if l["date"] == today), {})
merged = {**prev_today, **snap}
lines = sorted([l for l in lines if l["date"] != today] + [merged], key=lambda l: l["date"])
open("snapshots.jsonl", "w").write("".join(json.dumps(l) + "\n" for l in lines))
data["live_snapshots"] = lines
if any(v.get("ok") for v in data["refreshed"].values()): data["updated"] = stamp
json.dump(data, open("data.json", "w"), ensure_ascii=False, indent=1)
print("items", len(data["items"]), "updated", data["updated"])
