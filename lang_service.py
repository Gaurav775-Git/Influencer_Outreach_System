import os
import time
from pathlib import Path
from typing import List

import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openrouter import ChatOpenRouter
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

DATA = Path("data");   DATA.mkdir(exist_ok=True)
OUT  = Path("output"); OUT.mkdir(exist_ok=True)

MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("LLM_RETRIES", "2"))

llm = ChatOpenRouter(
    model=MODEL,
    temperature=0.7,
    timeout=TIMEOUT,
    max_retries=MAX_RETRIES,
)

BRAND = {
    "name": "YourBrand",
    "offer": "a paid UGC collaboration for our upcoming collection",
    "value": "you keep creative control, we pay per asset",
    "cta": "Open to a 15-min call this week?",
}


class CreatorOutput(BaseModel):
    themes: List[str] = Field(description="3-5 short content-theme tags")
    email_pitch: str = Field(description="Email body, 60-90 words")
    instagram_dm: str = Field(description="Instagram DM, 15-30 words")


prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You generate influencer outreach content. For each creator return JSON with:\n"
     "- themes: 3-5 short content-theme tags\n"
     "- email_pitch: 60-90 word warm email, no emojis, mentions niche + themes + audience fit + one collab angle\n"
     "- instagram_dm: 15-30 word DM, natural, max 1 emoji\n"
     "Return only valid JSON matching the schema."),
    ("human",
     "Brand: {brand}\n"
     "Creator: {name}\n"
     "Platform: {platform}\n"
     "Niche: {niche}\n"
     "Bio: {bio}"),
])


def _fallback(reason: str) -> dict:
    return {
        "content_themes": "Not Generated",
        "email_pitch": f"Not Generated ({reason})",
        "instagram_dm": f"Not Generated ({reason})",
        "email_word_count": 0,
        "dm_word_count": 0,
    }


def process_one(row: dict) -> dict:
    name = str(row.get("name", "")).strip()
    bio = str(row.get("biography", "")).strip()
    niche = str(row.get("niche", "")).strip() or "general"
    platform = str(row.get("platform", "")).strip()

    if not name:
        return _fallback("missing name")

    try:
        chain = prompt | llm.with_structured_output(CreatorOutput)
        out = chain.invoke({
            "brand": f"{BRAND['name']} - {BRAND['offer']} ({BRAND['value']}). {BRAND['cta']}",
            "name": name,
            "platform": platform,
            "niche": niche,
            "bio": bio[:800] if bio else "(no bio)",
        })
        email = out.email_pitch.strip()
        dm = out.instagram_dm.strip()
        return {
            "content_themes": ", ".join(out.themes[:5]),
            "email_pitch": email,
            "instagram_dm": dm,
            "email_word_count": len(email.split()),
            "dm_word_count": len(dm.split()),
        }
    except Exception as e:
        err_type = type(e).__name__
        msg = str(e)[:120]
        print(f"  [FAIL] {err_type}: {msg}")
        return _fallback(err_type)


def process(input_file: str = "filtered_influencers.xlsx"):
    src = OUT / input_file
    if not src.exists():
        print(f"[ERROR] {src} not found")
        return

    df = pd.read_excel(src)
    total = len(df)
    print(f"[INFO] loaded {total} rows from {src}")
    print(f"[INFO] model={MODEL}  timeout={TIMEOUT}s  retries={MAX_RETRIES}")

    results = []
    start = time.time()

    for i, row in df.iterrows():
        name = str(row.get("name", "")).strip()[:40]
        print(f"[{i+1}/{total}] {name}")
        t0 = time.time()
        res = process_one(row.to_dict())
        dt = time.time() - t0
        print(f"      -> {dt:.1f}s  themes={res['content_themes'][:50]}")
        results.append(res)

    elapsed = time.time() - start
    print(f"\n[INFO] total time: {elapsed:.1f}s  avg: {elapsed/total:.1f}s/row")

    res_df = pd.DataFrame(results)
    out_df = pd.concat([df.reset_index(drop=True), res_df], axis=1)

    data_out = out_df.drop(columns=["email_pitch", "instagram_dm",
                                    "email_word_count", "dm_word_count"])
    msg_out = out_df[["name", "email_pitch", "email_word_count",
                      "instagram_dm", "dm_word_count"]].copy()

    with pd.ExcelWriter(OUT / "influencers_enriched.xlsx", engine="openpyxl") as w:
        data_out.to_excel(w, sheet_name="Enriched", index=False)
    with pd.ExcelWriter(OUT / "messages.xlsx", engine="openpyxl") as w:
        msg_out.to_excel(w, sheet_name="Messages", index=False)

    print(f"[OK] wrote output/influencers_enriched.xlsx ({len(data_out)} rows)")
    print(f"[OK] wrote output/messages.xlsx ({len(msg_out)} rows)")


if __name__ == "__main__":
    process()