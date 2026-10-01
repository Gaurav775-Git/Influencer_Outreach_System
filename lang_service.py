import os
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
llm = ChatOpenRouter(model=MODEL, temperature=0.7)

BRAND = {
    "name": "YourBrand",
    "offer": "a paid UGC collaboration for our upcoming collection",
    "value": "you keep creative control, we pay per asset",
    "cta": "Open to a 15-min call this week?",
}


class ThemeList(BaseModel):
    themes: List[str] = Field(description="3-5 short content-theme tags")


class MessagePair(BaseModel):
    email_pitch: str = Field(description="Email body, 60-90 words")
    instagram_dm: str = Field(description="Instagram DM, 15-30 words")


theme_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You classify creator bios into 3-5 short content-theme tags. "
     "Return only valid JSON matching the schema."),
    ("human", "Niche: {niche}\nBio: {bio}"),
])

message_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Write personalized influencer outreach. "
     "EMAIL: 60-90 words, warm, no emojis, mention niche + themes + audience fit + one collaboration angle. "
     "DM: 15-30 words, natural, max 1 emoji, personalized. "
     "Return only valid JSON matching the schema."),
    ("human",
     "Brand: {brand}\n"
     "Creator: {name}\n"
     "Platform: {platform}\n"
     "Niche: {niche}\n"
     "Themes: {themes}"),
])


def classify_themes(bio: str, niche: str) -> list[str]:
    if not bio or not str(bio).strip():
        return [niche]
    try:
        chain = theme_prompt | llm.with_structured_output(ThemeList)
        out = chain.invoke({"niche": niche, "bio": str(bio)[:800]})
        return out.themes[:5] if out.themes else [niche]
    except Exception as e:
        print(f"  [theme fail] {e}")
        return [niche]


def generate_messages(name, platform, niche, themes) -> dict:
    try:
        chain = message_prompt | llm.with_structured_output(MessagePair)
        out = chain.invoke({
            "brand": f"{BRAND['name']} - {BRAND['offer']} ({BRAND['value']}). {BRAND['cta']}",
            "name": name,
            "platform": platform,
            "niche": niche,
            "themes": themes,
        })
        email = out.email_pitch.strip()
        dm = out.instagram_dm.strip()
        return {
            "email_pitch": email,
            "instagram_dm": dm,
            "email_word_count": len(email.split()),
            "dm_word_count": len(dm.split()),
        }
    except Exception as e:
        print(f"  [msg fail] {e}")
        return {
            "email_pitch": "Not Generated",
            "instagram_dm": "Not Generated",
            "email_word_count": 0,
            "dm_word_count": 0,
        }


def process(input_file: str = "filtered_influencers.xlsx"):
    src = OUT / input_file
    if not src.exists():
        print(f"[ERROR] {src} not found")
        return

    df = pd.read_excel(src)
    print(f"[INFO] loaded {len(df)} rows from {src}")

    themes_col, email_col, dm_col = [], [], []
    email_wc, dm_wc = [], []

    for i, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        bio = str(row.get("biography", "")).strip()
        niche = str(row.get("niche", "")).strip() or "general"
        platform = str(row.get("platform", "")).strip()

        print(f"[{i+1}/{len(df)}] {name}")

        themes = classify_themes(bio, niche)
        themes_col.append(", ".join(themes))

        msgs = generate_messages(name, platform, niche, ", ".join(themes))
        email_col.append(msgs["email_pitch"])
        dm_col.append(msgs["instagram_dm"])
        email_wc.append(msgs["email_word_count"])
        dm_wc.append(msgs["dm_word_count"])

    df["content_themes"] = themes_col
    df["email_pitch"] = email_col
    df["instagram_dm"] = dm_col
    df["email_word_count"] = email_wc
    df["dm_word_count"] = dm_wc

    data_out = df.drop(columns=["email_pitch", "instagram_dm",
                                "email_word_count", "dm_word_count"])
    msg_out = df[["name", "email_pitch", "email_word_count",
                  "instagram_dm", "dm_word_count"]].copy()

    with pd.ExcelWriter(OUT / "influencers_enriched.xlsx", engine="openpyxl") as w:
        data_out.to_excel(w, sheet_name="Enriched", index=False)
    with pd.ExcelWriter(OUT / "messages.xlsx", engine="openpyxl") as w:
        msg_out.to_excel(w, sheet_name="Messages", index=False)

    print(f"[OK] wrote output/influencers_enriched.xlsx ({len(data_out)} rows)")
    print(f"[OK] wrote output/messages.xlsx ({len(msg_out)} rows)")


if __name__ == "__main__":
    process()