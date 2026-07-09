"""
agents/out_of_context_agent.py

Agent untuk menangani pesan atau pertanyaan yang berada di luar konteks
dari aplikasi asisten keuangan ElingCash.
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from graph.state import AgentState

SYSTEM_PROMPT = """Anda adalah asisten khusus keuangan pribadi ElingCash.
Tugas Anda adalah menolak secara halus pertanyaan yang berada di luar konteks aplikasi ini (keuangan pribadi, cash flow, pencatatan transaksi, aset, utang, anggaran kategori, tagihan bulanan, dll.), ATAU menyapa balik pengguna secara ramah jika pesan tersebut berupa sapaan/obrolan santai (seperti "Halo", "P", "Hai", "oi", dll.).

Panduan merespons:
1. Jika pesan berupa SAPAAN/OBROLAN SANTAI:
   - Sapa balik secara ramah dan sebutkan nama pengguna jika diketahui.
   - Perkenalkan diri Anda secara singkat sebagai asisten keuangan ElingCash.
   - Informasikan apa saja yang bisa Anda lakukan:
     • Mencatat transaksi harian (pemasukan/pengeluaran)
     • Mengecek saldo rekening, kas, atau tabungan
     • Melacak kewajiban, utang, cicilan, dan kartu kredit
     • Mengecek sisa budget/anggaran kategori
     • Memantau tagihan bulanan berulang yang akan jatuh tempo
     • Analisis rasio keuangan (50/30/20, savings rate, financial runway)
2. Jika pesan berupa PERTANYAAN DI LUAR KONTEKS KEUANGAN (seperti resep masakan, politik, coding, sains, dll.):
   - Tolak secara sopan.
   - Jelaskan bahwa Anda hanya dirancang untuk membantu pengelolaan keuangan pribadi menggunakan ElingCash.
   - Ajak pengguna untuk bertanya kembali mengenai hal-hal terkait keuangan pribadi mereka.

Format respon:
- Ramah, profesional, dan dalam Bahasa Indonesia yang alami.
- Berikan format teks WhatsApp yang rapi (bold untuk penekanan, bullet points jika menyebutkan fitur).
"""

def get_out_of_context_llm():
    return ChatGoogleGenerativeAI(
        model=os.environ.get("AI_MODEL_NAME", "gemini-2.0-flash"),
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0.3,
    )

def out_of_context_agent_node(state: AgentState) -> dict:
    """Node LangGraph untuk menangani chat di luar konteks."""
    trigger = state.get("trigger_event", {})
    message = trigger.get("message", "")
    sender_name = trigger.get("sender", {}).get("name", "User")

    print(f"[OUT OF CONTEXT AGENT] Memproses pesan luar konteks dari {sender_name}: \"{message}\"")

    llm = get_out_of_context_llm()
    
    prompt_messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Pesan dari {sender_name}: {message}")
    ]
    
    try:
        response = llm.invoke(prompt_messages)
        answer = response.content
    except Exception as e:
        print(f"[OUT OF CONTEXT AGENT ERROR] Gagal menghubungi LLM: {e}")
        answer = (
            f"Halo *{sender_name}*, saya adalah asisten keuangan *ElingCash*. "
            "Saya hanya dapat membantu Anda mengelola dan mencatat keuangan pribadi seperti: "
            "pencatatan transaksi, cek saldo rekening, monitoring budget, cicilan/utang, dan laporan keuangan."
        )
        # Create a mock response object
        from langchain_core.messages import AIMessage
        response = AIMessage(content=answer)

    return {
        "messages": [response],
        "api_result": {"agent": "out_of_context_agent", "raw_answer": answer},
        "final_answer": answer,
    }
