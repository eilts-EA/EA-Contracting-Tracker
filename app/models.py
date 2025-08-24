
from typing import Optional, List, Literal
from datetime import datetime, date
from sqlmodel import SQLModel, Field, Column, JSON

Role = Literal["admin", "officer", "viewer"]

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(index=True, unique=True)
    role: Role = Field(default="officer", index=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

class Contract(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    number: str = Field(index=True)                  # e.g., RFQ/RFP/Contract number
    title: str = Field(index=True)
    agency: Optional[str] = Field(default=None, index=True)
    naics: Optional[str] = Field(default=None, index=True)
    set_aside: Optional[str] = Field(default=None, index=True)  # e.g., SDVOSB, 8(a), HUBZone
    description: Optional[str] = None
    status: str = Field(default="Draft", index=True) # Draft, Assigned, In Progress, Submitted, Awarded, Not Awarded, Closed
    officer_id: Optional[int] = Field(default=None, index=True, foreign_key="user.id")
    due_date: Optional[date] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    meta: Optional[dict] = Field(default=None, sa_column=Column(JSON))

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(index=True, foreign_key="contract.id")
    description: str
    status: str = Field(default="To Do", index=True)   # To Do, In Progress, Blocked, Done
    assigned_to: Optional[int] = Field(default=None, index=True, foreign_key="user.id")
    due_date: Optional[date] = Field(default=None, index=True)
    completed_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    notes: Optional[str] = None

class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    at: datetime = Field(default_factory=datetime.utcnow, index=True)
    user_id: Optional[int] = Field(default=None, index=True, foreign_key="user.id")
    actor: str = "system"
    action: str
    entity: str
    entity_id: Optional[int] = None
    before: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    after: Optional[dict] = Field(default=None, sa_column=Column(JSON))
