from typing import Optional, Literal

from pydantic import BaseModel


class QuestionModel(BaseModel):
    question: str
    subject: str
    use: str
    correct: Literal["A", "B", "C", "D"]
    responseA: str
    responseB: str
    responseC: str
    responseD: Optional[str]
    remark: Optional[str]
