"""
graph/state.py

Mendefinisikan AgentState TypedDict yang dibagikan antar seluruh node
dalam LangGraph StateGraph pipeline.
"""

import operator
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """
    State yang digunakan oleh seluruh node dalam LangGraph pipeline.

    Attributes:
        messages: Akumulasi pesan percakapan (AI, Human, Tool). 
                  Setiap node akan append ke list ini — tidak menggantikan.
        trigger_event: Payload trigger original dari WhatsApp client (JSON dict).
        intent: Klasifikasi intent yang ditentukan oleh Supervisor.
                Contoh: 'financial_profile', 'category_budget', dll.
        api_result: Hasil mentah yang dikembalikan oleh FinSight API
                    setelah sub-agent melakukan pemanggilan tool.
        final_answer: Jawaban akhir dalam Bahasa Indonesia yang telah
                      diformat oleh formatter node, siap dikirim ke WhatsApp.
    """
    messages: Annotated[list[BaseMessage], operator.add]
    trigger_event: dict
    intent: str
    api_result: dict
    final_answer: str
