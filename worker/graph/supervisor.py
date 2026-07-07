"""
graph/supervisor.py

Supervisor Node: Menggunakan Gemini 2.0 Flash dengan structured output
untuk mengklasifikasikan intent pesan WhatsApp dan merutekan ke sub-agent
yang tepat.
"""

import os
from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from graph.state import AgentState


# -------------------------------------------------------
# Definisi Intent yang valid
# -------------------------------------------------------
IntentType = Literal[
    "financial_profile",
    "transaction_history",
    "record_transaction",
    "category_budget",
    "dashboard_summary",
    "analytics",
    "assets",
    "out_of_context",
]


class RoutingDecision(BaseModel):
    """Schema structured output untuk keputusan routing Supervisor."""
    intent: IntentType = Field(
        description="Klasifikasi intent dari pesan pengguna."
    )
    reasoning: str = Field(
        description="Alasan singkat mengapa intent ini dipilih."
    )


# -------------------------------------------------------
# Prompt Supervisor
# -------------------------------------------------------
SUPERVISOR_SYSTEM_PROMPT = """Anda adalah Supervisor AI untuk aplikasi FinSight, asisten keuangan pribadi.
Tugas Anda adalah mengklasifikasikan intent dari pesan pengguna ke salah satu dari 8 kategori berikut:

1. **financial_profile** — Pertanyaan umum tentang kondisi keuangan: net worth, tabungan, savings rate, 
   financial runway, ringkasan aset, atau peringatan keuangan secara umum.
   Contoh: "Bagaimana kondisi keuangan saya?", "Berapa total kekayaan saya?", "Apakah saya punya warning?"

2. **transaction_history** — Riwayat atau daftar transaksi yang sudah terjadi, dengan filter apapun
   (tanggal, kategori, rekening, nominal, keyword deskripsi).
   Contoh: "Tampilkan pengeluaran bulan ini", "Transaksi apa saja kemarin?", "Pengeluaran makan minggu ini?"

3. **record_transaction** — Permintaan untuk mencatat atau memasukkan transaksi baru.
   Contoh: "Catat makan siang 50rb dari dompet", "Saya baru bayar listrik 300 ribu", "Tambahkan pemasukan gaji 5 juta"

4. **category_budget** — Pertanyaan tentang sisa alokasi budget atau limit per kategori pengeluaran.
   Contoh: "Berapa sisa budget makan saya?", "Apakah budget hobi masih ada?", "Sudah berapa persen budget transportasi terpakai?"

5. **dashboard_summary** — Ringkasan kondisi bulan berjalan, peringatan kritis, dan tagihan yang akan jatuh tempo.
   Contoh: "Ada notifikasi apa?", "Tagihan apa yang hampir jatuh tempo?", "Ringkasan keuangan hari ini?"

6. **analytics** — Analisis historis, tren jangka panjang (6 bulan), rasio 50/30/20, atau saran keuangan ilmiah.
   Contoh: "Tren pengeluaran 6 bulan terakhir?", "Bagaimana rasio kebutuhan vs keinginan saya?", "Saran untuk menghemat?"

7. **assets** — Informasi detail aset dan kewajiban: saldo rekening tertentu, daftar tabungan, investasi, atau utang.
   Contoh: "Berapa saldo BCA saya?", "Daftar semua rekening saya", "Berapa total utang saya?"

8. **out_of_context** — Semua pertanyaan, sapaan santai, obrolan kasual, atau permintaan lain yang sama sekali tidak berkaitan dengan cash flow, pencatatan transaksi, aset, utang, anggaran, atau laporan keuangan FinSight.
   Contoh: "Halo apa kabar?", "Siapa presiden Indonesia?", "Bagaimana cara membuat nasi goreng?", "Bisa bantu saya belajar coding?", "Ceritakan lelucon"

Klasifikasikan pesan berikut ke intent yang paling tepat. Jawab dengan JSON sesuai schema.
"""

SUPERVISOR_HUMAN_TEMPLATE = """Pesan dari pengguna WhatsApp:
Nama: {sender_name}
Pesan: {message}

Tentukan intent yang paling sesuai."""


# -------------------------------------------------------
# Inisialisasi LLM Supervisor
# -------------------------------------------------------
def _create_supervisor_chain():
    llm = ChatGoogleGenerativeAI(
        model=os.environ.get("AI_MODEL_NAME", "gemini-2.0-flash"),
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_SYSTEM_PROMPT),
        ("human", SUPERVISOR_HUMAN_TEMPLATE),
    ])
    return prompt | llm.with_structured_output(RoutingDecision)


_supervisor_chain = None


def get_supervisor_chain():
    """Lazy initialization untuk menghindari error saat import tanpa .env."""
    global _supervisor_chain
    if _supervisor_chain is None:
        _supervisor_chain = _create_supervisor_chain()
    return _supervisor_chain


# -------------------------------------------------------
# Supervisor Node Function
# -------------------------------------------------------
def supervisor_node(state: AgentState) -> dict:
    """
    Node supervisor yang mengklasifikasikan intent pesan.
    Dipanggil pertama kali dalam pipeline LangGraph.
    """
    trigger = state.get("trigger_event", {})
    message = trigger.get("message", "")
    sender_name = trigger.get("sender", {}).get("name", "User")

    print(f"[SUPERVISOR] Menganalisis pesan: \"{message}\"")

    chain = get_supervisor_chain()
    decision: RoutingDecision = chain.invoke({
        "message": message,
        "sender_name": sender_name,
    })

    print(f"[SUPERVISOR] Intent: {decision.intent} | Alasan: {decision.reasoning}")

    return {"intent": decision.intent}


# -------------------------------------------------------
# Routing Function untuk add_conditional_edges
# -------------------------------------------------------
def route_by_intent(state: AgentState) -> str:
    """Mengembalikan nama node berikutnya berdasarkan intent di state."""
    return state.get("intent", "financial_profile")
