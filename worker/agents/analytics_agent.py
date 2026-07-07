"""
agents/analytics_agent.py

Sub-agent untuk menjawab pertanyaan analisis keuangan historis dan mendalam:
tren 6 bulan, perkembangan net worth, rasio 50/30/20, savings rate,
financial runway, dan saran keuangan berbasis ilmiah.

Tool yang digunakan: get_analytics
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from graph.state import AgentState
from tools.finsight_tools import ANALYTICS_TOOLS

AGENT_SYSTEM_PROMPT = """Anda adalah Financial Analytics Specialist untuk aplikasi FinSight.

Tugas Anda:
- Mengambil data analisis historis menggunakan get_analytics
- Menginterpretasikan tren keuangan dan memberikan insight yang bermakna
- Memberikan saran keuangan berbasis data ilmiah (50/30/20 Rule, Emergency Fund, dll.)

Panduan format jawaban:
- Tampilkan tren yang relevan dengan pertanyaan pengguna
- Jika membahas rasio 50/30/20: jelaskan arti Needs/Wants/Savings
- Bandingkan dengan standar ideal (Savings Rate ideal: >20%, Emergency Fund ideal: 3-6 bulan)
- Sertakan saran dari data advice jika relevan
- Gunakan analogi sederhana untuk penjelasan keuangan yang kompleks
- Format nominal: Rp1.500.000
- Jawab dalam Bahasa Indonesia yang edukatif namun mudah dipahami

Referensi standar keuangan:
- Savings Rate baik: >20% dari pemasukan
- Financial Runway ideal: 3-6 bulan pengeluaran
- Rasio 50/30/20: 50% kebutuhan, 30% keinginan, 20% tabungan/investasi

SELALU gunakan tool get_analytics untuk mendapatkan data analisis terkini."""


def create_analytics_agent():
    llm = ChatGoogleGenerativeAI(
        model=os.environ.get("AI_MODEL_NAME", "gemini-2.0-flash"),
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0.2,
    )
    return create_react_agent(llm, ANALYTICS_TOOLS, prompt=AGENT_SYSTEM_PROMPT)


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = create_analytics_agent()
    return _agent


def analytics_agent_node(state: AgentState) -> dict:
    """Node LangGraph untuk Analytics Agent."""
    trigger = state.get("trigger_event", {})
    message = trigger.get("message", "")
    sender_name = trigger.get("sender", {}).get("name", "User")

    print(f"[ANALYTICS AGENT] Memproses: \"{message}\"")

    agent = get_agent()
    result = agent.invoke({
        "messages": [HumanMessage(content=f"{sender_name} bertanya: {message}")]
    })

    from utils import get_message_content_string
    last_message = result["messages"][-1]
    answer = get_message_content_string(last_message.content) if hasattr(last_message, "content") else str(last_message)

    return {
        "messages": result["messages"],
        "api_result": {"agent": "analytics_agent", "raw_answer": answer},
        "final_answer": answer,
    }
