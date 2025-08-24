
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import select
from .models import AuditLog, User

def as_dict(obj) -> Dict[str, Any]:
    if obj is None:
        return {}
    try:
        return obj.model_dump()
    except Exception:
        return dict(obj)

def log(session, *, user: Optional[User], action: str, entity: str, entity_id: Optional[int]=None, before=None, after=None):
    al = AuditLog(
        user_id=user.id if user else None,
        actor=(user.name if user else "system"),
        action=action,
        entity=entity,
        entity_id=entity_id,
        before=before,
        after=after
    )
    session.add(al)
    session.commit()

def find_user_by_email(session, email: str) -> Optional[User]:
    from sqlmodel import select
    return session.exec(select(User).where(User.email == email)).first()
