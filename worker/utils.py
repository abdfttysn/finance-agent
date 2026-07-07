"""
utils.py

Fungsi helper utilitas untuk seluruh sistem worker.
"""

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
