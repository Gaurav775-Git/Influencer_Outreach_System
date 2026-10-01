import argparse
import sys

from ui import banner, info, ok, warn, err

from fetch_youtube_data import fetch
from filter import run as run_filter
from lang_service import process as run_lang


def run_pipeline(niche, target):
    banner(f"MICRO-INFLUENCER OUTREACH  —  niche={niche}  target={target}")

    banner("STAGE 1 — DISCOVERY  (YouTube API)")
    try:
        df = fetch(niche=niche, target=target)
    except Exception as e:
        err(f"Discovery failed: {e}")
        sys.exit(1)
    if df.empty:
        err("No influencers discovered. Aborting.")
        sys.exit(1)
    ok(f"Discovered {len(df)} influencers")

    banner("STAGE 2 — FILTERING  (pandas)")
    try:
        passed, failed = run_filter(niche=niche)
    except Exception as e:
        err(f"Filtering failed: {e}")
        sys.exit(1)
    if passed is None or len(passed) == 0:
        err("No influencers passed filtering. Aborting.")
        sys.exit(1)
    ok(f"PASS: {len(passed)}   FAIL: {len(failed)}")

    banner("STAGE 3 — ENRICHMENT + PERSONALIZATION  (LangChain)")
    try:
        run_lang(input_file="filtered_influencers.xlsx")
    except Exception as e:
        err(f"LangChain stage failed: {e}")
        sys.exit(1)

    banner("PIPELINE COMPLETE")
    info("Output files:")
    print("  output/filtered_influencers.xlsx")
    print("  output/influencers_enriched.xlsx")
    print("  output/messages.xlsx")


def interactive():
    banner("Interactive Mode")
    niche  = input("Niche [fitness]: ").strip() or "fitness"
    target = input("How many influencers [50]: ").strip() or "50"
    try:
        target = int(target)
    except ValueError:
        target = 50
    run_pipeline(niche, target)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--niche",  default=None)
    p.add_argument("--target", type=int, default=50)
    a = p.parse_args()

    if a.niche:
        run_pipeline(a.niche, a.target)
    else:
        interactive()