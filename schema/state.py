# schema/state.py
import operator
from typing import Annotated, Sequence, TypedDict, Union, Literal
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # messages: Konuşma geçmişi. 'operator.add' sayesinde yeni mesajlar eskisinin üstüne eklenir (append).
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # next: Supervisor'ın bir sonraki adımda kimi çağırdığı bilgisini tutar.
    # ⚠️ BURADA Math_Agent EKLENDİ
    next: Union[str, Literal["HR_Agent", "IT_Agent", "Finance_Agent", "Math_Agent", "FINISH"]]