"""
main.py

FastAPI entry point untuk Worker. Menerima trigger webhook dari client,
menjalankan pipeline LangGraph, dan mengembalikan hasil formulasi asisten.
"""

import os
import sys
from dotenv import load_dotenv

# Load env variables before other imports
load_dotenv()

# Verify required environment variables
required_envs = ["GOOGLE_API_KEY", "ELINGCASH_TOKEN", "ELINGCASH_BASE_URL"]
missing_envs = [env for env in required_envs if not os.getenv(env)]
if missing_envs:
    print(f"⚠️ PERINGATAN: Variabel lingkungan berikut belum diisi: {', '.join(missing_envs)}")
    print("Pastikan untuk mengisi file .env sebelum menjalankan worker!")

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Add current path to python path to avoid import errors
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from graph.pipeline import app_graph
from langchain_core.messages import HumanMessage

app = FastAPI(
    title="ElingCash Multi-Agent Worker",
    description="Python LangGraph Worker to process WhatsApp triggers and route them to appropriate APIs",
    version="1.0.0"
)

# -------------------------------------------------------
# Schema Request & Response
# -------------------------------------------------------
class TriggerEventRequest(BaseModel):
    id: str
    message: str
    sender: dict  # {"name": "...", "jid": "..."}
    group: dict   # {"name": "...", "jid": "..."}
    keyword: Optional[str] = None
    timestamp: str

class ProcessResponse(BaseModel):
    answer: str
    intent: str
    success: bool

# -------------------------------------------------------
# Endpoints
# -------------------------------------------------------
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "api_connected": bool(os.getenv("ELINGCASH_TOKEN")),
        "gemini_configured": bool(os.getenv("GOOGLE_API_KEY"))
    }

@app.post("/process", response_model=ProcessResponse)
async def process_trigger(event: TriggerEventRequest):
    """
    Menerima trigger event dari WhatsApp client dan menjalankannya di LangGraph.
    """
    from utils import safe_print
    safe_print(f"\n[WORKER] Menerima event ID: {event.id} | Pesan: \"{event.message}\"")
    
    # 1. Konstruksi State Awal
    initial_state = {
        "messages": [HumanMessage(content=event.message)],
        "trigger_event": event.dict(),
        "intent": "",
        "api_result": {},
        "final_answer": ""
    }
    
    try:
        # 2. Jalankan LangGraph workflow secara asynchronous
        # Note: LangGraph support async invocation dengan ainvoke
        result = await app_graph.ainvoke(initial_state)
        
        # 3. Ambil jawaban akhir dan intent
        final_answer = result.get("final_answer", "Maaf, saya tidak dapat merumuskan jawaban.")
        intent = result.get("intent", "unknown")
        
        safe_print(f"[WORKER] Selesai memproses. Jawaban: \"{final_answer[:60]}...\"")
        
        return ProcessResponse(
            answer=final_answer,
            intent=intent,
            success=True
        )
        
    except Exception as e:
        print(f"[WORKER ERROR] Gagal menjalankan pipeline: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat memproses pesan: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("WORKER_HOST", "0.0.0.0")
    port = int(os.getenv("WORKER_PORT", "8000"))
    
    print(f"Memulai server Worker di http://{host}:{port} ...")
    uvicorn.run("main:app", host=host, port=port, reload=True)
