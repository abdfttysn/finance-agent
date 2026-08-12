"""
utils.py

Fungsi helper utilitas untuk seluruh sistem worker.
"""

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

def get_message_content_string(content) -> str:
    """
    Mengonversi content dari BaseMessage (yang bisa berupa str atau list)
    secara aman menjadi string tunggal.
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
        return "\n".join(parts)
    elif content is None:
        return ""
    return str(content)


def safe_print(message: str):
    """
    Mencetak pesan secara aman ke stdout, mengganti karakter yang tidak didukung
    (seperti emoji) untuk mencegah UnicodeEncodeError di Windows.
    """
    try:
        print(message.encode('ascii', errors='replace').decode('ascii'))
    except Exception:
        pass


class TokenCounterCallbackHandler(BaseCallbackHandler):
    """
    Callback handler untuk menghitung token secara otomatis dari semua model
    yang dipanggil selama siklus eksekusi LangGraph.
    """
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        for generations in response.generations:
            for generation in generations:
                # Coba ambil usage_metadata standar LangChain
                if hasattr(generation.message, "usage_metadata") and generation.message.usage_metadata:
                    usage = generation.message.usage_metadata
                    self.prompt_tokens += usage.get("input_tokens", 0)
                    self.completion_tokens += usage.get("output_tokens", 0)
                    self.total_tokens += usage.get("total_tokens", 0)
                # Fallback ke response_metadata jika usage_metadata tidak terisi
                elif hasattr(generation.message, "response_metadata") and "token_usage" in generation.message.response_metadata:
                    usage = generation.message.response_metadata["token_usage"]
                    self.prompt_tokens += usage.get("prompt_tokens", 0)
                    self.completion_tokens += usage.get("completion_tokens", 0)
                    self.total_tokens += usage.get("total_tokens", 0)

