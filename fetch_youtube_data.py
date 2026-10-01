import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
DATA = Path("data"); DATA.mkdir(exist_ok=True)

MIN_FOLLOWERS = 5_000
MAX_FOLLOWERS = 100_000

NICHE_KEYWORDS = {
    "fashion":   ["fashion haul", "outfit ideas", "streetwear style",
                  "thrift fashion", "style tips", "fashion vlog"],
    "beauty":    ["skincare routine", "makeup tutorial", "beauty review",
                  "GRWM", "skincare tips", "makeup routine"],
    "fitness":   ["home workout", "fitness routine", "gym motivation",
                  "workout tips", "weight loss journey", "fitness vlog"],
    "tech":      ["tech review", "gadget unboxing", "coding tutorial",
                  "tech tips", "software review", "developer vlog"],
    "gaming":    ["gameplay", "gaming review", "walkthrough",
                  "gaming tips", "indie game", "game review"],
    "lifestyle": ["day in my life", "morning routine", "lifestyle vlog",
                  "productivity tips", "self care routine", "daily vlog"],
    "crypto":    ["crypto explained", "bitcoin analysis",
                  "crypto news", "blockchain tutorial", "defi explained"],
    "fintech":   ["personal finance", "investing basics",
                  "money tips", "budgeting", "financial freedom"],
    "parenting": ["mom life", "parenting tips", "family vlog",
                  "baby care", "parenting hacks"],
}


def _yt():
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY not set in .env")
    return build("youtube", "v3", developerKey=API_KEY)


def search_channel_ids(youtube, keyword, max_results=50):
    ids = []
    try:
        resp = youtube.search().list(
            q=keyword, part="snippet", type="channel",
            maxResults=min(max_results, 10)
        ).execute()
        for item in resp.get("items", []):
            ids.append(item["snippet"]["channelId"])
    except Exception as e:
        print(f"    search failed '{keyword}': {e}")
    return ids


def get_recent_titles(youtube, uploads_playlist_id, max_titles=2):
    titles = []
    try:
        resp = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="snippet",
            maxResults=max_titles
        ).execute()
        for item in resp.get("items", []):
            title = item["snippet"].get("title", "").strip()
            if title:
                titles.append(title)
    except Exception as e:
        print(f"    recent titles failed: {e}")
    return titles


def fetch_channel_stats(youtube, channel_ids):
    out = []
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i+50]
        try:
            resp = youtube.channels().list(
                id=",".join(batch),
                part="snippet,statistics,brandingSettings,contentDetails"
            ).execute()
            for ch in resp.get("items", []):
                stats = ch.get("statistics", {})
                subs = stats.get("subscriberCount")
                if not subs:
                    continue
                subs = int(subs)
                if subs < MIN_FOLLOWERS or subs > MAX_FOLLOWERS:
                    continue

                snip = ch["snippet"]
                uploads = (ch.get("contentDetails", {})
                             .get("relatedPlaylists", {})
                             .get("uploads"))

                recent = get_recent_titles(youtube, uploads, 2) if uploads else []
                time.sleep(0.2)

                out.append({
                    "name":           snip["title"],
                    "handle":         snip.get("customUrl", "").lstrip("@"),
                    "platform":       "YouTube",
                    "profile_url":    f"https://youtube.com/channel/{ch['id']}",
                    "channel_id":     ch["id"],
                    "follower_count": subs,
                    "video_count":    int(stats.get("videoCount", 0)),
                    "total_views":    int(stats.get("viewCount", 0)),
                    "biography":      snip.get("description", ""),
                    "country":        snip.get("country", "Not Available"),
                    "recent_titles":  " | ".join(recent) if recent else "Not Available",
                    "source":         "youtube_api",
                })
        except Exception as e:
            print(f"    batch failed: {e}")
        time.sleep(0.3)
    return out


def fetch(niche="fitness", target=50):
    print(f"[YouTube] niche='{niche}' target={target}")

    youtube = _yt()
    keywords = NICHE_KEYWORDS.get(niche, [niche])

    candidate_ids = []
    seen = set()

    for kw in keywords:
        if len(candidate_ids) >= target * 6:
            break
        print(f"  searching: {kw}")
        for cid in search_channel_ids(youtube, kw, max_results=50):
            if cid not in seen:
                seen.add(cid)
                candidate_ids.append(cid)
        time.sleep(0.5)

    print(f"[YouTube] collected {len(candidate_ids)} unique channel IDs")

    channels = fetch_channel_stats(youtube, candidate_ids)
    print(f"[YouTube] {len(channels)} channels in micro range ({MIN_FOLLOWERS}-{MAX_FOLLOWERS})")

    if not channels:
        print("[YouTube] No channels in range. Widen keywords or follower range.")
        return pd.DataFrame()

    df = pd.DataFrame(channels)
    df["niche"] = niche

    if len(df) > target:
        df = df.head(target)

    out = DATA / "raw_influencers.xlsx"
    df.to_excel(out, index=False)
    print(f"[YouTube] saved {len(df)} rows -> {out}")
    return df


if __name__ == "__main__":
    import sys
    niche = sys.argv[1] if len(sys.argv) > 1 else "fitness"
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    fetch(niche=niche, target=target)