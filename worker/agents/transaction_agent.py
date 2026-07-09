"""
agents/transaction_agent.py

Sub-agent untuk menjawab pertanyaan tentang riwayat transaksi pengguna.
Agent ini mampu menyusun filter yang tepat (tanggal, kategori, tipe, nominal,
keyword) berdasarkan konteks pertanyaan pengguna secara natural.

Tool yang digunakan: get_transactions
"""

import os
from datetime import date
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from graph.state import AgentState
from tools.elingcash_tools import TRANSACTION_TOOLS

AGENT_SYSTEM_PROMPT = f"""Anda adalah Transaction History Specialist untuk aplikasi ElingCash.

Tugas Anda:
- Mengambil riwayat transaksi pengguna menggunakan filter yang tepat sesuai pertanyaan
- Menginterpretasikan dan merangkum data transaksi dengan jelas
- Menjawab pertanyaan berbasis data transaksi aktual

Panduan penggunaan filter get_transactions:
- Hari ini: start_date = end_date = tanggal hari ini ({date.today().isoformat()})
- Bulan ini: start_date = awal bulan ini, end_date = hari ini
- Minggu ini: start_date = 7 hari lalu, end_date = hari ini
- Transaksi pengeluaran: type = 'expense'
- Transaksi pemasukan: type = 'income'
- Pencarian kata kunci: gunakan parameter search
- Filter berdasarkan rekening sumber: gunakan asset_id
- Filter berdasarkan rekening target/penerima cicilan: gunakan target_asset_id
- Filter histori lengkap cicilan/mutasi utang/transfer yang melibatkan suatu rekening (baik sebagai sumber atau target): gunakan involved_asset_id. PENTING: Jika user bertanya tentang riwayat cicilan suatu kewajiban/utang tertentu, cari dulu asset_id kewajiban tersebut menggunakan get_assets() dengan keyword nama kewajibannya, lalu masukkan ke parameter involved_asset_id.
- Rentang tanggal MAKSIMAL 1 tahun (366 hari)

Panduan format jawaban:
- Jawab dalam Bahasa Indonesia yang natural
- Tampilkan transaksi dalam format yang mudah dibaca. Jika transaksi memiliki rekening target, tampilkan aliran dana dengan visualisasi `[Sumber] ➔ [Target]` (Contoh: `BCA ➔ Cicilan Laptop`).
- Jika banyak transaksi, rangkum dengan total dan highlight transaksi terbesar
- Format nominal: Rp1.500.000 (bukan 1500000)

Tanggal hari ini: {date.today().isoformat()}"""


def create_transaction_agent():
    llm = ChatGoogleGenerativeAI(
        model=os.environ.get("AI_MODEL_NAME", "gemini-2.0-flash"),
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0.1,
    )
    return create_react_agent(llm, TRANSACTION_TOOLS, prompt=AGENT_SYSTEM_PROMPT)


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = create_transaction_agent()
    return _agent


def transaction_agent_node(state: AgentState) -> dict:
    """Node LangGraph untuk Transaction Agent."""
    trigger = state.get("trigger_event", {})
    message = trigger.get("message", "")
    sender_name = trigger.get("sender", {}).get("name", "User")

    print(f"[TRANSACTION AGENT] Memproses: \"{message}\"")

    agent = get_agent()
    result = agent.invoke({
        "messages": [HumanMessage(content=f"{sender_name} bertanya: {message}")]
    })

    from utils import get_message_content_string
    last_message = result["messages"][-1]
    answer = get_message_content_string(last_message.content) if hasattr(last_message, "content") else str(last_message)

    return {
        "messages": result["messages"],
        "api_result": {"agent": "transaction_agent", "raw_answer": answer},
        "final_answer": answer,
    }
