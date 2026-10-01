import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DATA = Path("data");   DATA.mkdir(exist_ok=True)
OUT  = Path("output"); OUT.mkdir(exist_ok=True)

MIN_FOLLOWERS = 5_000
MAX_FOLLOWERS = 100_000
MIN_ENGAGEMENT = 0.01

NICHE_TERMS = {
    "fitness":   ["workout", "fitness", "gym", "training", "exercise",
                  "weight", "muscle", "yoga", "run", "cardio", "diet", "nutrition"],
    "fashion":   ["fashion", "style", "outfit", "clothing", "wear",
                  "streetwear", "thrift", "haul"],
    "beauty":    ["beauty", "makeup", "skincare", "cosmetic", "glow",
                  "serum", "routine"],
    "tech":      ["tech", "gadget", "software", "coding", "developer",
                  "review", "programming", "ai"],
    "gaming":    ["gaming", "game", "gameplay", "streamer", "esports",
                  "twitch", "console"],
    "lifestyle": ["lifestyle", "vlog", "daily", "routine", "productivity"],
    "crypto":    ["crypto", "bitcoin", "blockchain", "defi", "web3"],
    "fintech":   ["finance", "investing", "money", "budget", "wealth"],
    "parenting": ["parenting", "mom", "dad", "baby", "family", "kids"],
}


def _estimate_engagement(row) -> float | None:
    subs = row.get("follower_count")
    views = row.get("total_views")
    videos = row.get("video_count")
    if not subs or not views or not videos or videos == 0:
        return None
    return round((views / videos) / subs, 4)


def _matches_niche(bio: str, niche: str) -> bool:
    if not isinstance(bio, str) or not bio.strip():
        return False
    terms = NICHE_TERMS.get(niche.lower(), [niche.lower()])
    bio_lower = bio.lower()
    return any(re.search(rf"\b{re.escape(t)}\b", bio_lower) for t in terms)


def _has_email(bio: str) -> bool:
    if not isinstance(bio, str):
        return False
    return bool(re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", bio))


def filter_dataframe(df: pd.DataFrame, niche: str):
    passed, failed = [], []

    for _, row in df.iterrows():
        reasons = []

        followers = row.get("follower_count")
        if pd.isna(followers):
            reasons.append("followers missing")
        elif not (MIN_FOLLOWERS <= int(followers) <= MAX_FOLLOWERS):
            reasons.append(f"followers {int(followers)} out of range")

        bio = row.get("biography", "")
        if not _matches_niche(bio, niche):
            reasons.append("niche mismatch in bio")

        er = _estimate_engagement(row)
        if er is not None and er < MIN_ENGAGEMENT:
            reasons.append(f"engagement {er} < {MIN_ENGAGEMENT}")

        rec = row.to_dict()
        rec["engagement_rate"] = er
        rec["has_email"] = _has_email(bio)
        rec["filter_status"] = "PASS" if not reasons else "FAIL"
        rec["filter_reasons"] = "; ".join(reasons) if reasons else ""

        (passed if not reasons else failed).append(rec)

    return pd.DataFrame(passed), pd.DataFrame(failed)


def run(input_file="raw_influencers.xlsx", niche=None):
    src = DATA / input_file
    if not src.exists():
        print(f"[ERROR] {src} not found. Run fetch_youtube_data.py first.")
        return

    df = pd.read_excel(src)
    print(f"[INFO] loaded {len(df)} rows from {src}")

    if niche is None:
        niche = df["niche"].iloc[0] if "niche" in df.columns and len(df) else "fitness"
    print(f"[INFO] filtering for niche: {niche}")

    passed, failed = filter_dataframe(df, niche)

    print(f"[OK] PASS: {len(passed)}   FAIL: {len(failed)}")

    if len(passed):
        print("\nQualified influencers:")
        cols = ["name", "platform", "follower_count", "engagement_rate", "has_email"]
        cols = [c for c in cols if c in passed.columns]
        print(passed[cols].to_string(index=False))

    with pd.ExcelWriter(OUT / "filtered_influencers.xlsx", engine="openpyxl") as w:
        passed.to_excel(w, sheet_name="Qualified", index=False)
        failed.to_excel(w, sheet_name="Rejected", index=False)

    print(f"\n[OK] saved -> output/filtered_influencers.xlsx")
    return passed, failed


if __name__ == "__main__":
    import sys
    niche = sys.argv[1] if len(sys.argv) > 1 else None
    run(niche=niche)