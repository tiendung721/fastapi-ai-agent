from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Section(BaseModel):
    start_row: int
    end_row: int
    header_row: int
    label: Optional[str] = None

class SessionData(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    file_path: Optional[str] = None
    auto_sections: List[Section] = Field(default_factory=list)
    confirmed_sections: Optional[List[Section]] = None
    used_rule: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)