"""
agents/assets_agent.py

Sub-agent untuk menjawab pertanyaan tentang daftar aset dan kewajiban pengguna:
saldo rekening tertentu, daftar semua tabungan/investasi, total utang,
atau pencarian rekening berdasarkan nama.

Tool yang digunakan: get_assets
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from graph.state import AgentState
from tools.elingcash_tools import ASSETS_TOOLS

AGENT_SYSTEM_PROMPT = """Anda adalah Asset & Liability Specialist untuk aplikasi ElingCash.

Tugas Anda:
- Mengambil data aset dan kewajiban pengguna menggunakan get_assets
- Menjawab pertanyaan tentang saldo rekening, daftar tabungan, investasi, atau utang

Panduan penggunaan get_assets:
- Jika pengguna menyebut nama rekening tertentu, gunakan keyword untuk filter
  Contoh: "saldo BCA" → get_assets(keyword="BCA")
  Contoh: "saldo dompet" → get_assets(keyword="dompet")
  Contoh: "kartu kredit" → get_assets(keyword="kartu kredit")
- Jika menanyakan semua aset atau kewajiban, panggil tanpa filter

Panduan format jawaban:
- Tampilkan nama rekening, tipe, dan saldo dengan jelas
- Tipe rekening:
  * liquid = Aset Lancar (kas, tabungan)
  * non_liquid = Aset Tidak Lancar (investasi, emas, properti)
  * liability = Kewajiban/Utang (kartu kredit, pinjaman)
- Saldo negatif = kewajiban/utang
- Hitung total aset vs total kewajiban jika relevan
- Format nominal: Rp1.500.000
- Jawab dalam Bahasa Indonesia yang natural dan informatif

SELALU gunakan tool get_assets untuk data terkini."""


def create_assets_agent():
    llm = ChatGoogleGenerativeAI(
        model=os.environ.get("AI_MODEL_NAME", "gemini-2.0-flash"),
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0.1,
    )
    return create_react_agent(llm, ASSETS_TOOLS, prompt=AGENT_SYSTEM_PROMPT)


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = create_assets_agent()
    return _agent


def assets_agent_node(state: AgentState) -> dict:
    """Node LangGraph untuk Assets Agent."""
    trigger = state.get("trigger_event", {})
    message = trigger.get("message", "")
    sender_name = trigger.get("sender", {}).get("name", "User")

    print(f"[ASSETS AGENT] Memproses: \"{message}\"")

    agent = get_agent()
    result = agent.invoke({
        "messages": [HumanMessage(content=f"{sender_name} bertanya: {message}")]
    })

    from utils import get_message_content_string
    last_message = result["messages"][-1]
    answer = get_message_content_string(last_message.content) if hasattr(last_message, "content") else str(last_message)

    return {
        "messages": result["messages"],
        "api_result": {"agent": "assets_agent", "raw_answer": answer},
        "final_answer": answer,
    }
