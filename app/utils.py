from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import select

from models import AuditLog, User

def as_dict(obj) -> Dict[str, Any]:
    if obj is None:
        return {}
    return {c: getattr(obj, c) for c in obj.__table__.columns.keys()}

def log(session, user_id: int, action: str):
    entry = AuditLog(user_id=user_id, action=action, timestamp=datetime.utcnow())
    session.add(entry)
    session.commit()

def find_user_by_email(session, email: str) -> Optional[User]:
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()
