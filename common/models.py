from typing import Optional, List
from pydantic import BaseModel, Field

class Section(BaseModel):
    start_row: int
    end_row: int
    header_row: int
    label: Optional[str] = None
    

class SessionData(BaseModel):
    session_id: str
    file_path: str
    user_id: Optional[str] = None

    
    used_rule: Optional[bool] = False

   
    auto_sections: List[Section] = Field(default_factory=list)
    confirmed_sections: List[Section] = Field(default_factory=list)

    
    confirming: Optional[bool] = False
    confirmed: Optional[bool] = False
    rule_version: Optional[str] = None
    fingerprint: Optional[str] = None
