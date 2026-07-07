"""
agents/financial_profile_agent.py

Sub-agent untuk menjawab pertanyaan profil keuangan umum pengguna:
net worth, savings rate, financial runway, daftar aset ringkasan,
peringatan budget aktif, dan tagihan belum terbayar.

Tool yang digunakan: get_financial_profile
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from graph.state import AgentState
from tools.finsight_tools import FINANCIAL_PROFILE_TOOLS

AGENT_SYSTEM_PROMPT = """Anda adalah Financial Profile Specialist untuk aplikasi FinSight.

Tugas Anda:
- Mengambil data profil keuangan lengkap pengguna menggunakan tool yang tersedia
- Menginterpretasikan data tersebut sesuai pertanyaan pengguna
- Memberikan jawaban faktual dan akurat berdasarkan data dari API

Panduan format jawaban:
- Jawab dalam Bahasa Indonesia yang natural dan mudah dipahami
- Sertakan angka yang relevan dan format dengan jelas (contoh: Rp1.500.000)
- Jika ada peringatan anggaran aktif, sebutkan dengan jelas
- Jawaban singkat dan langsung pada poin yang ditanyakan

SELALU gunakan tool get_financial_profile untuk mendapatkan data terkini."""


def create_financial_profile_agent():
    llm = ChatGoogleGenerativeAI(
        model=os.environ.get("AI_MODEL_NAME", "gemini-2.0-flash"),
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0.1,
    )
    return create_react_agent(llm, FINANCIAL_PROFILE_TOOLS, prompt=AGENT_SYSTEM_PROMPT)


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = create_financial_profile_agent()
    return _agent


def financial_profile_agent_node(state: AgentState) -> dict:
    """Node LangGraph untuk Financial Profile Agent."""
    trigger = state.get("trigger_event", {})
    message = trigger.get("message", "")
    sender_name = trigger.get("sender", {}).get("name", "User")

    print(f"[FINANCIAL PROFILE AGENT] Memproses: \"{message}\"")

    agent = get_agent()
    result = agent.invoke({
        "messages": [HumanMessage(content=f"{sender_name} bertanya: {message}")]
    })

    # Ambil pesan terakhir dari agent sebagai hasil
    from utils import get_message_content_string
    last_message = result["messages"][-1]
    answer = get_message_content_string(last_message.content) if hasattr(last_message, "content") else str(last_message)

    return {
        "messages": result["messages"],
        "api_result": {"agent": "financial_profile_agent", "raw_answer": answer},
        "final_answer": answer,
    }
