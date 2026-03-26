# schema/state.py
import operator
from typing import Annotated, Sequence, TypedDict, Union, Literal, Optional, Dict, List

from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # messages: Konuşma geçmişi. 'operator.add' sayesinde yeni mesajlar eskisinin üstüne eklenir (append).
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # next: Supervisor'ın bir sonraki adımda kimi çağırdığı bilgisini tutar.
    next: Union[str, Literal["HR_Agent", "IT_Agent", "Finance_Agent", "Math_Agent", "General_Agent", "FINISH"]]

    # user_context: OpenWebUI'den gelen kullanıcı bilgileri (email, isim, tarih)
    user_context: Optional[Dict[str, str]]

    # visited_agents: Zaten calistirilmis agent listesi (dongu onleme)
    visited_agents: Optional[List[str]]

    # shared_context: Agent'lar arasi paylasimli veri deposu
    # Her agent kendi sonuclarini buraya yazar, diger agent'lar okuyabilir
    # Ornek: {"HR": {"kalan_izin": 15, "izin_talebi": "onay_bekliyor"}, "Finance": {"avans": 5000}}
    shared_context: Optional[Dict[str, Dict]]

    # plan_steps: Supervisor tarafindan ilk adimda uretilen checklist plani
    plan_steps: Optional[List[Dict[str, str]]]
