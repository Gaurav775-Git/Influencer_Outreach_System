import os
from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter

load_dotenv()

model = ChatOpenRouter(
    model="openrouter/free",
    temperature=0.7,
)

response = model.invoke("Say hello in one short sentence.")
print(response.content)