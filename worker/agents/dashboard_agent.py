"""
agents/dashboard_agent.py

Sub-agent untuk menjawab pertanyaan tentang kondisi keuangan bulan berjalan:
KPI bulanan, peringatan limit anggaran kritis, dan tagihan yang mendekat.

Tool yang digunakan: get_dashboard_summary
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from graph.state import AgentState
from tools.elingcash_tools import DASHBOARD_TOOLS

AGENT_SYSTEM_PROMPT = """Anda adalah Dashboard Operations Specialist untuk aplikasi ElingCash.

Tugas Anda:
- Mengambil data dashboard bulan berjalan menggunakan get_dashboard_summary
- Menjawab pertanyaan tentang kondisi keuangan terkini, peringatan, dan tagihan

Panduan format jawaban:
- Tampilkan KPI utama: pemasukan, pengeluaran, dan sisa budget bulan ini
- Jika ada peringatan budget kritis, tampilkan dengan jelas menggunakan ⚠️
- Jika ada tagihan mendekat atau overdue, tampilkan dengan 🔔 atau 🚨
- Format nominal: Rp1.500.000
- Jawab dalam Bahasa Indonesia yang ringkas namun informatif

Contoh format jawaban dashboard:
"📊 *Ringkasan Keuangan Bulan Ini*
• Pemasukan: Rp16.200.000
• Pengeluaran: Rp7.000.000  
• Sisa Budget: Rp3.600.000

⚠️ *Peringatan Budget:*
• Makanan sudah 92% dari limit

🔔 *Tagihan Mendekat:*
• Internet Indihome — Rp380.000 (jatuh tempo 2 hari lagi)"

SELALU gunakan tool get_dashboard_summary untuk data terkini."""


def create_dashboard_agent():
    llm = ChatGoogleGenerativeAI(
        model=os.environ.get("AI_MODEL_NAME", "gemini-2.0-flash"),
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0.1,
    )
    return create_react_agent(llm, DASHBOARD_TOOLS, prompt=AGENT_SYSTEM_PROMPT)


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = create_dashboard_agent()
    return _agent


def dashboard_agent_node(state: AgentState) -> dict:
    """Node LangGraph untuk Dashboard Agent."""
    trigger = state.get("trigger_event", {})
    message = trigger.get("message", "")
    sender_name = trigger.get("sender", {}).get("name", "User")

    print(f"[DASHBOARD AGENT] Memproses: \"{message}\"")

    agent = get_agent()
    result = agent.invoke({
        "messages": [HumanMessage(content=f"{sender_name} bertanya: {message}")]
    })

    from utils import get_message_content_string
    last_message = result["messages"][-1]
    answer = get_message_content_string(last_message.content) if hasattr(last_message, "content") else str(last_message)

    return {
        "messages": result["messages"],
        "api_result": {"agent": "dashboard_agent", "raw_answer": answer},
        "final_answer": answer,
    }
