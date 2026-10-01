from langchain_openrouter import ChatOpenRouter
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List

class ThemeList(BaseModel):
    themes: List[str] = Field(description="3-5 short content-theme tags")


class MessagePair(BaseModel):
    email_pitch: str = Field(description="30-50 word email body")
    instagram_dm: str = Field(description="15-30 word DM")


llm = ChatOpenRouter(model="meta-llama/llama-3.3-70b-instruct:free", temperature=0.7)

theme_prompt = ChatPromptTemplate.from_messages([
    ("system", "Classify creator bios into 3-5 content theme tags."),
    ("human", "Niche: {niche}\nBio: {bio}"),
])

message_prompt = ChatPromptTemplate.from_messages([
    ("system", "Write an email pitch (30-50 words) and an Instagram DM (15-30 words)."),
    ("human", "Creator: {name} | Niche: {niche} | Themes: {themes} | Brand: {brand}"),
])


def classify_themes(bio: str, niche: str) -> list[str]:
    chain = theme_prompt | llm.with_structured_output(ThemeList)
    return chain.invoke({"niche": niche, "bio": bio}).themes


def generate_messages(name: str, niche: str, themes: str, brand: str) -> dict:
    chain = message_prompt | llm.with_structured_output(MessagePair)
    out = chain.invoke({"name": name, "niche": niche, "themes": themes, "brand": brand})
    return {
        "email_pitch": out.email_pitch,
        "instagram_dm": out.instagram_dm,
    }