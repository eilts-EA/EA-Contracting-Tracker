from typing import Optional, List, Literal
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

Role = Literal["admin", "officer", "viewer"]

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    role: Role = "viewer"
    contracts: List["Contract"] = Relationship(back_populates="owner")

class Contract(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
    owner: Optional[User] = Relationship(back_populates="contracts")

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str
    completed: bool = False
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")

class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    action: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
