"""
agents/category_budget_agent.py

Sub-agent untuk menjawab pertanyaan tentang sisa alokasi budget per kategori.
Mampu mencari kategori berdasarkan keyword dari pertanyaan pengguna.

Tool yang digunakan: get_categories
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from graph.state import AgentState
from tools.elingcash_tools import CATEGORY_BUDGET_TOOLS

AGENT_SYSTEM_PROMPT = """Anda adalah Budget Category Specialist untuk aplikasi ElingCash.

Tugas Anda:
- Mengambil informasi sisa alokasi budget per kategori menggunakan tool get_categories
- Menjawab pertanyaan tentang budget yang tersedia, terpakai, dan tersisa

Panduan penggunaan get_categories:
- Jika pengguna menyebut nama kategori tertentu, gunakan parameter keyword untuk filter
  Contoh: "sisa makan" → get_categories(keyword="makan")
  Contoh: "budget transport" → get_categories(keyword="transport")  
  Contoh: "budget hiburan" → get_categories(keyword="hiburan")
- Jika pengguna menanyakan semua kategori, panggil tanpa filter
- Filter type='expense' untuk kategori pengeluaran

Panduan format jawaban:
- Tampilkan nama kategori, budget limit, jumlah terpakai, dan sisa dengan jelas
- Gunakan emoji status:
  * 🟢 0–60% terpakai: Aman
  * 🟡 61–85% terpakai: Perlu Hati-Hati
  * 🔴 86–100%+ terpakai: Kritis / Melebihi Batas
- Format nominal: Rp1.500.000
- Sertakan persentase pemakaian
- Jawab dalam Bahasa Indonesia yang natural"""


def create_category_budget_agent():
    llm = ChatGoogleGenerativeAI(
        model=os.environ.get("AI_MODEL_NAME", "gemini-2.0-flash"),
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0.1,
    )
    return create_react_agent(llm, CATEGORY_BUDGET_TOOLS, prompt=AGENT_SYSTEM_PROMPT)


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = create_category_budget_agent()
    return _agent


def category_budget_agent_node(state: AgentState) -> dict:
    """Node LangGraph untuk Category Budget Agent."""
    trigger = state.get("trigger_event", {})
    message = trigger.get("message", "")
    sender_name = trigger.get("sender", {}).get("name", "User")

    print(f"[CATEGORY BUDGET AGENT] Memproses: \"{message}\"")

    agent = get_agent()
    result = agent.invoke({
        "messages": [HumanMessage(content=f"{sender_name} bertanya: {message}")]
    })

    from utils import get_message_content_string
    last_message = result["messages"][-1]
    answer = get_message_content_string(last_message.content) if hasattr(last_message, "content") else str(last_message)

    return {
        "messages": result["messages"],
        "api_result": {"agent": "category_budget_agent", "raw_answer": answer},
        "final_answer": answer,
    }
