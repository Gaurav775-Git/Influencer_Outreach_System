import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd
from colorama import Fore, Style, init
from tabulate import tabulate

init(autoreset=True)

DATA = Path("data");   DATA.mkdir(exist_ok=True)
OUT  = Path("output"); OUT.mkdir(exist_ok=True)


def banner(text):
    print(f"\n{Fore.CYAN}{'═' * 60}\n  {text}\n{'═' * 60}{Style.RESET_ALL}")

def info(msg): print(f"{Fore.BLUE}[INFO]{Style.RESET_ALL} {msg}")
def ok(msg):   print(f"{Fore.GREEN}[ OK ]{Style.RESET_ALL} {msg}")
def warn(msg): print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {msg}")
def err(msg):  print(f"{Fore.RED}[FAIL]{Style.RESET_ALL} {msg}")

def table(rows, headers):
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))


def _save(name, obj):
    (DATA / name).write_text(json.dumps(obj, indent=2, default=str))
    info(f"saved data/{name}")


def discover(niche, target):
    info(f"[stub] discovering {target} '{niche}' influencers")
    return [
        {
            "name": f"Demo Creator {i}",
            "handle": f"demo_creator_{i}",
            "platform": "YouTube",
            "profile_url": f"https://youtube.com/@demo_creator_{i}",
            "follower_count": 10_000 + i * 500,
            "biography": f"Fitness creator #{i} sharing workout tips. contact{i}@example.com",
            "niche": niche,
            "source": "stub",
        }
        for i in range(1, target + 1)
    ]


def filter_influencers(records, niche):
    info("[stub] filtering")
    passed = [{**r, "filter_status": "PASS", "filter_reasons": "",
               "engagement_rate": None} for r in records]
    return passed, []


def enrich(records, niche):
    info("[stub] enriching")
    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    out = []
    for r in records:
        m = EMAIL_RE.search(r.get("biography", ""))
        out.append({
            **r,
            "contact_email": m.group(0) if m else "Not Found",
            "content_themes": f"{niche}, demo-theme",
            "website": "Not Found",
            "audience_age": "Not Available",
            "audience_gender": "Not Available",
            "audience_geo": "Not Available",
        })
    return out


def personalize(records, brand):
    info("[stub] generating messages")
    out = []
    for r in records:
        email = (f"Hi {r['name']}, loved your {r['niche']} content. "
                 f"We'd love to collaborate with {brand['name']} on {brand['offer']}. "
                 f"{brand['cta']}")
        dm = f"Hey {r['name']}! Loved your {r['niche']} posts — open to a quick collab?"
        out.append({**r,
                    "email_pitch": email, "instagram_dm": dm,
                    "email_word_count": len(email.split()),
                    "dm_word_count": len(dm.split())})
    return out


def send(records, subject):
    info(f"[stub] DRY RUN — subject: {subject}")
    for r in records:
        email = r.get("contact_email", "Not Found")
        status = "skipped_no_email" if email == "Not Found" else "simulated"
        ok(f"{status} -> {email}")


def export(personalized, failed):
    df_all = pd.DataFrame([{
        "Name": r["name"], "Platform": r["platform"],
        "Profile URL": r["profile_url"], "Followers": r["follower_count"],
        "Engagement Rate": r["engagement_rate"], "Niche": r["niche"],
        "Content Themes": r["content_themes"], "Contact Email": r["contact_email"],
        "Source": r["source"], "Filter Status": "PASS",
    } for r in personalized])

    df_msg = pd.DataFrame([{
        "Name": r["name"], "Email": r["contact_email"],
        "Email Pitch": r["email_pitch"], "Email Words": r["email_word_count"],
        "Instagram DM": r["instagram_dm"], "DM Words": r["dm_word_count"],
    } for r in personalized])

    with pd.ExcelWriter(OUT / "influencers.xlsx", engine="openpyxl") as w:
        df_all.to_excel(w, sheet_name="Qualified", index=False)
    with pd.ExcelWriter(OUT / "messages.xlsx", engine="openpyxl") as w:
        df_msg.to_excel(w, sheet_name="Messages", index=False)

    ok(f"influencers.xlsx -> {len(df_all)} rows")
    ok(f"messages.xlsx    -> {len(df_msg)} rows")


def run(niche, target, brand_name):
    banner(f"Micro-Influencer Outreach — niche={niche}, target={target}")

    banner("STAGE 1 — DISCOVERY")
    raw = discover(niche, target)
    if not raw:
        err("No influencers discovered."); sys.exit(1)
    _save("raw_influencers.json", raw)

    banner("STAGE 2 — FILTERING")
    passed, failed = filter_influencers(raw, niche)
    _save("filtered_influencers.json", {"passed": passed, "failed": failed})
    if not passed:
        err("No influencers passed filter."); sys.exit(1)

    banner("STAGE 3 — ENRICHMENT")
    enriched = enrich(passed, niche)
    _save("enriched_influencers.json", enriched)

    banner("STAGE 4 — PERSONALIZATION")
    brand = {
        "name": brand_name,
        "offer": "a paid UGC collaboration for our upcoming collection",
        "value": "you keep creative control, we pay per asset",
        "cta": "Open to a 15-min call this week?",
    }
    personalized = personalize(enriched, brand)
    _save("personalized.json", personalized)

    banner("STAGE 5 — SENDING")
    send(personalized, subject=f"Collab with {brand_name}?")

    banner("STAGE 6 — EXPORT")
    export(personalized, failed)

    banner("PIPELINE COMPLETE")
    info("Review output/*.xlsx")


def interactive():
    banner("Interactive Mode")
    niche  = input("Niche [fitness]: ").strip() or "fitness"
    target = input("How many influencers [5]: ").strip() or "5"
    brand  = input("Brand name [YourBrand]: ").strip() or "YourBrand"
    run(niche, int(target), brand)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--niche",  default=None)
    p.add_argument("--target", type=int, default=5)
    p.add_argument("--brand",  default="YourBrand")
    a = p.parse_args()

    if a.niche:
        run(a.niche, a.target, a.brand)
    else:
        interactive()