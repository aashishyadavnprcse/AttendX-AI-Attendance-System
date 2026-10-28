from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    name: str
    email: str
    role: str


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None
