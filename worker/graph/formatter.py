"""
graph/formatter.py

Node terakhir dalam pipeline LangGraph yang memformulasikan jawaban akhir.
Jika sub-agent sudah memformat jawaban dengan baik, node ini akan meneruskannya.
Jika belum, node ini akan menggunakan LLM untuk menyusun jawaban yang rapi.
"""

import os
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from graph.state import AgentState

_formatter_llm = None

def get_formatter_llm():
    global _formatter_llm
    if _formatter_llm is None:
        _formatter_llm = ChatGoogleGenerativeAI(
            model=os.environ.get("AI_MODEL_NAME", "gemini-2.0-flash"),
            google_api_key=os.environ["GOOGLE_API_KEY"],
            temperature=0.2,
        )
    return _formatter_llm

def response_formatter_node(state: AgentState) -> dict:
    """
    Node untuk memastikan output terformat dengan rapi untuk WhatsApp.
    """
    from utils import get_message_content_string
    final_answer = get_message_content_string(state.get("final_answer", ""))
    
    # Jika sub-agent sudah menghasilkan jawaban final_answer, langsung gunakan
    if final_answer and not final_answer.startswith("{"):
        print("[FORMATTER] Meneruskan jawaban dari sub-agent.")
        return {"final_answer": final_answer}
        
    print("[FORMATTER] Menyusun ulang jawaban dari log percakapan...")
    messages = state.get("messages", [])
    
    # Gunakan LLM Formatter untuk merapikan seluruh chat history menjadi satu jawaban WhatsApp
    llm = get_formatter_llm()
    
    system_instruction = (
        "Anda adalah asisten WhatsApp FinSight. Rangkum informasi dari chat history "
        "menjadi satu jawaban yang ringkas, padat, ramah, dan berformat rapi (gunakan bullet points, "
        "bold text untuk penekanan, dan emoji minimal). "
        "Jawab langsung dalam Bahasa Indonesia. Jangan sebutkan nama tool atau detail teknis system."
    )
    
    prompt_messages = [
        AIMessage(content=system_instruction)
    ] + messages[-4:]  # Ambil beberapa pesan terakhir
    
    try:
        response = llm.invoke(prompt_messages)
        formatted_answer = response.content
    except Exception as e:
        print(f"[FORMATTER] Error: {e}. Menggunakan fallback.")
        # Fallback menggunakan pesan terakhir
        if messages:
            formatted_answer = messages[-1].content
        else:
            formatted_answer = "Maaf, saya tidak dapat merumuskan jawaban saat ini."
            
    return {"final_answer": formatted_answer}
