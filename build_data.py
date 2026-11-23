#!/usr/bin/env python3
"""Build data.json from Erin's roundup xlsx files.
Usage: python3 build_data.py [history.xlsx] [weekly1.xlsx ...]
First file = full history; later weekly files add/override weekly-summary rows."""
import sys, json, datetime as dt, openpyxl
ROOT = "/workspace/samBest360-content/roundups/"
files = sys.argv[1:] or [ROOT + "roundup-history-to-2026-11-23.xlsx", ROOT + "roundup-2026-11-16.xlsx"]
D = lambda x: x.strftime("%Y-%m-%d") if isinstance(x, (dt.datetime, dt.date)) else None
def rows(ws):
    it = ws.iter_rows(values_only=True); h = next(it)
    return [dict(zip(h, r)) for r in it if any(c is not None for c in r)]
num = lambda x: x if isinstance(x, (int, float)) else None
wbs = [openpyxl.load_workbook(f, data_only=True) for f in files]
hist = wbs[0]
items = []; asof = []
for r in rows(hist["Shorts"]):
    p = r["Platform"] or ""
    plat = "TikTok" if p == "TikTok" else "YouTube" if p.startswith("YouTube") else None
    if not plat or r["Status"] not in ("posted", "removed") or num(r["Views"]) is None: continue
    t = r["Scheduled/Posted time (SAST)"]
    items.append(dict(title=r["Title/Topic"], platform=plat, date=D(r["Date"]),
        time=t.strftime("%H:%M") if isinstance(t, dt.datetime) else (t if isinstance(t, str) and len(t) == 5 else ""),
        game=r["Game"] or "Other", type=r["Video type"] or "Other", live=r["Status"] == "posted",
        views=r["Views"], likes=num(r["Likes"]), comments=num(r["Comments"]), link=r["Link"] if str(r["Link"]).startswith("http") else None,
        kind="long-form" if p == "YouTube long-form" else "short"))
    if isinstance(r["Stats as-of (SAST)"], dt.datetime): asof.append(r["Stats as-of (SAST)"])
for r in rows(hist["Streams & VODs"]):
    v = num(r["VOD views (Twitch)"])
    if v is None: continue
    items.append(dict(title=f'{r["Game"]} stream ({r["Length"]})', platform="Twitch", date=D(r["Date"]), time=str(r["Start (SAST)"])[:5],
        game=r["Game"], type="Stream VOD", live=True, views=v, likes=None, comments=None, link=f'https://www.twitch.tv/videos/{str(r["Stream/VOD id"]).lstrip("v")}', kind="vod"))
snap = []; 
for r in rows(hist["Channel Stats"]):
    a = r["As-of (SAST)"]
    if isinstance(a, dt.datetime):
        asof.append(a)
        snap.append(dict(channel=r["Channel"], asof=a.strftime("%Y-%m-%d %H:%M"), followers=num(r["Followers/Subscribers"]) if num(r["Followers/Subscribers"]) is not None else (int(r["Followers/Subscribers"]) if str(r["Followers/Subscribers"]).isdigit() else None),
            total_views=num(r["Total views"]), total_likes=num(r["Total likes"]), views7=r["7-day views (as shown)"] if r["7-day views (as shown)"] != "not recorded" else None))
weekly = {}
for wb in wbs:
    for r in rows(wb["Weekly Summary"]):
        if isinstance(r["Week"], dt.datetime) and any(v is not None for k, v in r.items() if k not in ("Week", "Notes")):
            weekly[D(r["Week"])] = {k: (D(v) if isinstance(v, dt.datetime) else v) for k, v in r.items()}
def cols(r): return {k: v for k, v in r.items()}
att = json.load(open(__file__.rsplit("/", 1)[0] + "/attention.json")) if "/" in __file__ else json.load(open("attention.json"))
open_flags = [dict(post=r["Post/Short"], platform=r["Platform"], issue=r["Issue"], action=r["Action taken"]) for r in rows(hist["Copyright Flags"]) if r["Status"] == "open"]
open_blockers = [dict(blocker=r["Blocker"], owner=r["Owner"], raised=D(r["Raised date"]), notes=r["Notes"]) for r in rows(hist["Blockers"]) if r["Status"] == "open"]
out = dict(updated=max(asof).strftime("%Y-%m-%d %H:%M") if asof else None, items=items, snapshots=snap, weekly=[weekly[k] for k in sorted(weekly)],
           attention=att["items"], open_flags=open_flags, open_blockers=open_blockers, sources=[f.split("/")[-1] for f in files])
json.dump(out, open("data.json", "w"), ensure_ascii=False, indent=1)
print("items", len(items), "snapshots", len(snap), "weeks", len(weekly), "updated", out["updated"])
