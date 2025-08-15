from pydantic import BaseModel, Field
from typing import List, Optional

class LearnedRule(BaseModel):
    label: str
    start_keywords: List[str] = Field(default_factory=list)
    end_keywords: List[str] = Field(default_factory=list)
    header_row: int
    tolerance: Optional[int] = 0
