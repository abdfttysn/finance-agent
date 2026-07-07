"""
agents/store_transaction_agent.py

Sub-agent untuk mencatat transaksi baru dari permintaan pengguna.
Agent ini menggunakan 3 tools secara berurutan:
  1. get_assets()     — untuk menemukan asset_id dari nama rekening yang disebutkan
  2. get_categories() — untuk menemukan category_id dari nama kategori yang disebutkan
  3. record_transaction() — untuk mencatat transaksi setelah ID ditemukan

Tool yang digunakan: get_assets, get_categories, record_transaction
"""

import os
from datetime import date
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from graph.state import AgentState
from tools.finsight_tools import STORE_TRANSACTION_TOOLS

AGENT_SYSTEM_PROMPT = f"""Anda adalah Transaction Recording Specialist untuk aplikasi FinSight.

Tugas Anda: Mencatat transaksi baru berdasarkan permintaan pengguna secara akurat.

ALUR WAJIB — Ikuti langkah ini secara berurutan:

LANGKAH 1 — Temukan Rekening Sumber (Asset ID) & Rekening Target (Target Asset ID, Jika Ada):
- Gunakan get_assets() dengan keyword dari nama rekening sumber yang disebutkan pengguna (contoh: 'BCA', 'dompet').
- Jika transaksi berupa pembayaran cicilan, pelunasan utang, pembayaran kartu kredit, atau transfer antar rekening, temukan juga Rekening Target (target_asset_id) menggunakan get_assets() dengan keyword rekening target yang disebutkan (contoh: 'Cicilan Laptop', 'Kredit Mandiri').
- Jika rekening sumber tidak disebutkan, gunakan get_assets() tanpa filter lalu pilih rekening utama (liquid balance terbesar).

LANGKAH 2 — Temukan Kategori (Category ID):
- Gunakan get_categories() dengan keyword dari nama kategori yang disebutkan pengguna (contoh: 'tagihan', 'makan').
- Tentukan type: 'expense' untuk pengeluaran, 'income' untuk pemasukan.
- Pilih kategori yang paling relevan dari hasil.

LANGKAH 3 — Catat Transaksi:
- Setelah asset_id, category_id, dan target_asset_id (jika ada) ditemukan, panggil record_transaction().
- Pastikan asset_id dan target_asset_id bernilai berbeda.
- Tanggal hari ini: {date.today().isoformat()} (gunakan ini jika tanggal tidak disebutkan).
- type: 'expense' untuk pengeluaran, 'income' untuk pemasukan.

Panduan format jawaban setelah berhasil:
- Konfirmasi transaksi berhasil dicatat dengan ringkasan: nominal, kategori, rekening sumber, rekening target (jika ada), tanggal.
- Format nominal: Rp50.000.
- Jika ada transfer/pembayaran target, gunakan visualisasi: `[Sumber] ➔ [Target]` (Contoh: `BCA ➔ Cicilan Laptop`).
- Jika gagal, jelaskan alasannya dengan jelas.

Contoh jawaban sukses cicilan:
"✅ Transaksi pembayaran cicilan berhasil dicatat!
• Nominal: Rp1.000.000
• Jenis: Pengeluaran
• Kategori: Sewa & Tagihan Bulanan
• Aliran Rekening: Rekening BCA ➔ Cicilan Laptop
• Tanggal: {date.today().isoformat()}
• Keterangan: Pembayaran cicilan Laptop"

Tanggal hari ini: {date.today().isoformat()}"""


def create_store_transaction_agent():
    llm = ChatGoogleGenerativeAI(
        model=os.environ.get("AI_MODEL_NAME", "gemini-2.0-flash"),
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0,
    )
    return create_react_agent(llm, STORE_TRANSACTION_TOOLS, prompt=AGENT_SYSTEM_PROMPT)


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = create_store_transaction_agent()
    return _agent


def store_transaction_agent_node(state: AgentState) -> dict:
    """Node LangGraph untuk Store Transaction Agent."""
    trigger = state.get("trigger_event", {})
    message = trigger.get("message", "")
    sender_name = trigger.get("sender", {}).get("name", "User")

    print(f"[STORE TRANSACTION AGENT] Memproses: \"{message}\"")

    agent = get_agent()
    result = agent.invoke({
        "messages": [HumanMessage(content=f"{sender_name} meminta: {message}")]
    })

    from utils import get_message_content_string
    last_message = result["messages"][-1]
    answer = get_message_content_string(last_message.content) if hasattr(last_message, "content") else str(last_message)

    return {
        "messages": result["messages"],
        "api_result": {"agent": "store_transaction_agent", "raw_answer": answer},
        "final_answer": answer,
    }
