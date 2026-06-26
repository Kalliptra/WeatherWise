"""LLM örnekleri — her rolün ayrı temperature değeri var."""

import os

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

_api_key = os.getenv("OPENAI_API_KEY")

# Yaratıcı öneri üretimi
react_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    openai_api_key=_api_key,
)

# Katı kalite denetimi
evaluator_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    openai_api_key=_api_key,
)

# Niyet sınıflandırma (deterministik + hızlı; hata/timeout'ta kural tabanlı yedeğe düşülür)
classifier_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    max_retries=1,  # her mesajda çalışır → yavaş çağrıda hızlıca yedeğe düş
    timeout=8,
    openai_api_key=_api_key,
)

# Deterministik araç planlaması
planner_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    openai_api_key=_api_key,
)

# Zaman planı üretimi (düşük sıcaklık → tutarlı format)
itinerary_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    openai_api_key=_api_key,
)
