
from sqlmodel import select
from .db import create_db_and_tables, get_session
from .models import User, Contract, Task
from datetime import date

def main():
    create_db_and_tables()
    with get_session() as s:
        # Seed users if empty
        if not s.exec(select(User)).first():
            s.add_all([
                User(name="Admin", email="admin@example.com", role="admin"),
                User(name="Officer One", email="officer1@example.com", role="officer"),
                User(name="Viewer", email="viewer@example.com", role="viewer"),
            ])
            s.commit()

        # Seed a sample contract if none
        if not s.exec(select(Contract)).first():
            officer = s.exec(select(User).where(User.role=="officer")).first()
            c = Contract(
                number="W56HZV-25-R-0001",
                title="Vehicle Maintenance Support",
                agency="DoD",
                naics="811111",
                set_aside="SDVOSB",
                description="Preventative maintenance and on-demand repairs.",
                status="Assigned",
                officer_id=officer.id if officer else None,
                due_date=date.today()
            )
            s.add(c); s.commit(); s.refresh(c)
            s.add_all([
                Task(contract_id=c.id, description="Review solicitation and amendments", status="In Progress", assigned_to=officer.id if officer else None),
                Task(contract_id=c.id, description="Draft technical volume", status="To Do", assigned_to=officer.id if officer else None),
            ])
            s.commit()
    print("Database initialized with demo data.")

if __name__ == "__main__":
    main()
