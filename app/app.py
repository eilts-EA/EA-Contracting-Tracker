
import io
from datetime import datetime, date
import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
from sqlmodel import select

from db import create_db_and_tables, get_session
from models import User, Contract, Task, AuditLog
from utils import as_dict, log, find_user_by_email

st.set_page_config(page_title="Contract Workflow Manager", layout="wide")

# --- DB bootstrap ---
create_db_and_tables()

# --- Auth helpers ---
def get_auth_user():
    # If Streamlit Authenticator is configured in secrets, use it.
    if "credentials" in st.secrets:
        creds = st.secrets["credentials"]
        cookie = st.secrets.get("cookie", {})
        authenticator = stauth.Authenticate(
            credentials=creds,
            cookie_name=cookie.get("name", "contract_workflow_auth"),
            key=cookie.get("key", "CHANGEME"),
            cookie_expiry_days=int(cookie.get("expiry_days", 14)),
        )
        name, auth_status, username = authenticator.login("Login", "main")
        if auth_status:
            st.session_state["authenticator"] = authenticator
            with get_session() as s:
                # Pull email from creds; keys differ by username
                u_meta = creds["usernames"][username]
                email = u_meta.get("email")
                user = find_user_by_email(s, email) if email else None
                if not user and email:
                    # auto-provision user if not present
                    role = "officer"
                    user = User(name=u_meta.get("name", username), email=email, role=role, active=True)
                    s.add(user); s.commit(); s.refresh(user)
            return user
        elif auth_status is False:
            st.error("Invalid credentials")
            return None
        else:
            st.info("Please log in")
            return None
    else:
        # Demo login fallback
        st.sidebar.info("Demo Login (secrets not configured)")
        with get_session() as s:
            users = s.exec(select(User).where(User.active==True).order_by(User.role, User.name)).all()
        choice = st.sidebar.selectbox("Select user", users, format_func=lambda u: f"{u.name} ({u.role})")
        return choice

current_user = get_auth_user()
if current_user is None:
    st.stop()

# Logout when authenticator is available
if "authenticator" in st.session_state:
    st.sidebar.button("Logout", on_click=st.session_state["authenticator"].logout, kwargs={"location":"sidebar"})

# --- Sidebar Navigation ---
st.sidebar.title("Contract Workflow")
section = st.sidebar.radio("Go to", ["My Dashboard", "Contracts", "Tasks", "Reports", "Audit Log", "Admin"] if current_user.role=="admin" else ["My Dashboard", "Contracts", "Tasks", "Reports"])

# --- Utility lookups ---
def list_users():
    with get_session() as s:
        return s.exec(select(User).where(User.active==True).order_by(User.name)).all()

def list_officers():
    with get_session() as s:
        return s.exec(select(User).where((User.role=="officer") & (User.active==True)).order_by(User.name)).all()

# --- My Dashboard ---
if section == "My Dashboard":
    st.title(f"Welcome, {current_user.name}")
    with get_session() as s:
        my_contracts = s.exec(select(Contract).where(Contract.officer_id == current_user.id).order_by(Contract.updated_at.desc())).all()
        my_tasks = s.exec(select(Task).where(Task.assigned_to == current_user.id).order_by(Task.updated_at.desc())).all()

    st.subheader("Assigned Contracts")
    st.dataframe(pd.DataFrame([as_dict(c) for c in my_contracts]), use_container_width=True)

    st.subheader("My Tasks")
    st.dataframe(pd.DataFrame([as_dict(t) for t in my_tasks]), use_container_width=True)

# --- Contracts ---
elif section == "Contracts":
    st.title("Contracts")
    # Filters
    colf1, colf2, colf3, colf4 = st.columns([2,2,2,2])
    with get_session() as s:
        status_filter = colf1.selectbox("Status", ["All","Draft","Assigned","In Progress","Submitted","Awarded","Not Awarded","Closed"])
        officer_list = list_officers()
        officer_names = ["All"] + [f"{u.id}:{u.name}" for u in officer_list]
        officer_choice = colf2.selectbox("Officer", officer_names)
        agency = colf3.text_input("Agency contains")
        naics = colf4.text_input("NAICS equals")

        q = select(Contract)
        if status_filter != "All":
            q = q.where(Contract.status == status_filter)
        if officer_choice != "All":
            officer_id = int(officer_choice.split(":")[0])
            q = q.where(Contract.officer_id == officer_id)
        if agency:
            q = q.where(Contract.agency.contains(agency))
        if naics:
            q = q.where(Contract.naics == naics)

        rows = s.exec(q.order_by(Contract.updated_at.desc())).all()

    st.dataframe(pd.DataFrame([as_dict(r) for r in rows]), use_container_width=True)

    st.markdown("---")
    st.subheader("Add / Edit Contract")
    mode = st.radio("Mode", ["Add new", "Edit existing"])

    if mode == "Add new":
        with st.form("add_contract", clear_on_submit=True):
            number = st.text_input("Contract Number", help="RFP/RFQ/Contract identifier")
            title = st.text_input("Title")
            agency = st.text_input("Agency")
            naics = st.text_input("NAICS")
            set_aside = st.text_input("Set-aside (e.g., SDVOSB)")
            description = st.text_area("Description")
            status = st.selectbox("Status", ["Draft","Assigned","In Progress","Submitted","Awarded","Not Awarded","Closed"], index=0)
            officer_sel = st.selectbox("Assign Officer", ["Unassigned"] + [f"{u.id}:{u.name}" for u in officer_list])
            due = st.date_input("Due Date", value=None)
            submitted = st.form_submit_button("Create Contract")

            if submitted:
                if not number.strip() or not title.strip():
                    st.error("Contract number and title are required.")
                else:
                    with get_session() as s:
                        officer_id = None if officer_sel == "Unassigned" else int(officer_sel.split(":")[0])
                        c = Contract(
                            number=number.strip(), title=title.strip(), agency=agency or None, naics=naics or None,
                            set_aside=set_aside or None, description=description or None, status=status,
                            officer_id=officer_id, due_date=due if due else None,
                            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
                        )
                        s.add(c); s.commit(); s.refresh(c)
                        log(s, user=current_user, action="create", entity="Contract", entity_id=c.id, after=as_dict(c))
                        st.success(f"Created contract #{c.id}: {c.number}")

    else:
        with get_session() as s:
            all_contracts = s.exec(select(Contract).order_by(Contract.updated_at.desc())).all()
        if not all_contracts:
            st.info("No contracts yet.")
        else:
            sel = st.selectbox("Choose contract", all_contracts, format_func=lambda c: f"#{c.id} {c.number} — {c.title}")
            with st.form("edit_contract"):
                number = st.text_input("Contract Number", value=sel.number or "")
                title = st.text_input("Title", value=sel.title or "")
                agency = st.text_input("Agency", value=sel.agency or "")
                naics = st.text_input("NAICS", value=sel.naics or "")
                set_aside = st.text_input("Set-aside", value=sel.set_aside or "")
                description = st.text_area("Description", value=sel.description or "")
                status_choices = ["Draft","Assigned","In Progress","Submitted","Awarded","Not Awarded","Closed"]
                status = st.selectbox("Status", status_choices, index=status_choices.index(sel.status if sel.status else "Draft"))
                officer_list = list_officers()
                officer_map = {u.id: u.name for u in officer_list}
                current_officer_display = officer_map.get(sel.officer_id, None)
                officer_sel = st.selectbox("Assign Officer", ["Unassigned"] + [f"{u.id}:{u.name}" for u in officer_list],
                                           index=0 if not current_officer_display else ( [f"{u.id}:{u.name}" for u in officer_list].index(f"{sel.officer_id}:{current_officer_display}") + 1 ))
                due = st.date_input("Due Date", value=sel.due_date)
                submitted = st.form_submit_button("Save Changes")
                if submitted:
                    with get_session() as s:
                        db_c = s.get(Contract, sel.id)
                        before = as_dict(db_c)
                        db_c.number = number.strip() or db_c.number
                        db_c.title = title.strip() or db_c.title
                        db_c.agency = agency or None
                        db_c.naics = naics or None
                        db_c.set_aside = set_aside or None
                        db_c.description = description or None
                        db_c.status = status
                        db_c.officer_id = None if officer_sel == "Unassigned" else int(officer_sel.split(":")[0])
                        db_c.due_date = due if due else None
                        db_c.updated_at = datetime.utcnow()
                        s.add(db_c); s.commit(); s.refresh(db_c)
                        log(s, user=current_user, action="update", entity="Contract", entity_id=db_c.id, before=before, after=as_dict(db_c))
                        st.success(f"Saved contract #{db_c.id}")
            if current_user.role == "admin":
                if st.button("Delete this contract"):
                    with get_session() as s:
                        db_c = s.get(Contract, sel.id)
                        if db_c:
                            before = as_dict(db_c)
                            s.delete(db_c); s.commit()
                            log(s, user=current_user, action="delete", entity="Contract", entity_id=sel.id, before=before, after=None)
                            st.success(f"Deleted contract #{sel.id}")

# --- Tasks ---
elif section == "Tasks":
    st.title("Tasks")
    with get_session() as s:
        # Filters
        colf1, colf2, colf3, colf4 = st.columns([2,2,2,2])
        status_filter = colf1.selectbox("Status", ["All","To Do","In Progress","Blocked","Done"])
        my_only = colf2.checkbox("Assigned to me only", value=(current_user.role!="admin"))
        due_before = colf3.date_input("Due before", value=None)
        contract_id = colf4.text_input("Contract ID filter")

        q = select(Task)
        if status_filter != "All":
            q = q.where(Task.status == status_filter)
        if my_only:
            q = q.where(Task.assigned_to == current_user.id)
        if due_before:
            q = q.where(Task.due_date <= due_before)
        if contract_id.strip():
            try:
                q = q.where(Task.contract_id == int(contract_id.strip()))
            except:
                pass

        tasks = s.exec(q.order_by(Task.updated_at.desc())).all()
        st.dataframe(pd.DataFrame([as_dict(t) for t in tasks]), use_container_width=True)

    st.markdown("---")
    st.subheader("Add Task")
    with get_session() as s:
        contract_options = s.exec(select(Contract).order_by(Contract.id.desc())).all()
        user_options = list_users()

    with st.form("add_task", clear_on_submit=True):
        contract_sel = st.selectbox("Contract", contract_options, format_func=lambda c: f"#{c.id} {c.number}")
        description = st.text_input("Description")
        status = st.selectbox("Status", ["To Do","In Progress","Blocked","Done"], index=0)
        assignee = st.selectbox("Assignee", ["Unassigned"] + [f"{u.id}:{u.name}" for u in user_options])
        due = st.date_input("Due Date", value=None)
        submitted = st.form_submit_button("Create Task")
        if submitted:
            with get_session() as s:
                t = Task(
                    contract_id=contract_sel.id, description=description.strip(),
                    status=status, assigned_to=None if assignee=="Unassigned" else int(assignee.split(":")[0]),
                    due_date=due if due else None, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
                )
                s.add(t); s.commit(); s.refresh(t)
                log(s, user=current_user, action="create", entity="Task", entity_id=t.id, after=as_dict(t))
                st.success(f"Created task #{t.id} for contract #{contract_sel.id}")

    st.subheader("Edit Task")
    with get_session() as s:
        all_tasks = s.exec(select(Task).order_by(Task.updated_at.desc())).all()
    if not all_tasks:
        st.info("No tasks to edit.")
    else:
        sel = st.selectbox("Choose task", all_tasks, format_func=lambda t: f"#{t.id} [{t.status}] {t.description[:40]}... (C#{t.contract_id})")
        with st.form("edit_task"):
            description = st.text_input("Description", value=sel.description or "")
            status = st.selectbox("Status", ["To Do","In Progress","Blocked","Done"], index=["To Do","In Progress","Blocked","Done"].index(sel.status))
            users = list_users()
            assignee = st.selectbox("Assignee", ["Unassigned"] + [f"{u.id}:{u.name}" for u in users],
                                    index=0 if not sel.assigned_to else ( [f"{u.id}:{u.name}" for u in users].index(f"{sel.assigned_to}:{[u.name for u in users if u.id==sel.assigned_to][0]}")+1 if any(u.id==sel.assigned_to for u in users) else 0))
            due = st.date_input("Due Date", value=sel.due_date)
            submitted = st.form_submit_button("Save Task")
            if submitted:
                with get_session() as s:
                    db_t = s.get(Task, sel.id)
                    before = as_dict(db_t)
                    db_t.description = description.strip() or db_t.description
                    db_t.status = status
                    db_t.assigned_to = None if assignee=="Unassigned" else int(assignee.split(":")[0])
                    db_t.due_date = due if due else None
                    db_t.updated_at = datetime.utcnow()
                    if status == "Done" and not db_t.completed_at:
                        db_t.completed_at = datetime.utcnow()
                    s.add(db_t); s.commit(); s.refresh(db_t)
                    log(s, user=current_user, action="update", entity="Task", entity_id=db_t.id, before=before, after=as_dict(db_t))
                    st.success(f"Saved task #{db_t.id}")
        if current_user.role == "admin":
            if st.button("Delete this task"):
                with get_session() as s:
                    db_t = s.get(Task, sel.id)
                    if db_t:
                        before = as_dict(db_t)
                        s.delete(db_t); s.commit()
                        log(s, user=current_user, action="delete", entity="Task", entity_id=sel.id, before=before, after=None)
                        st.success(f"Deleted task #{sel.id}")

# --- Reports ---
elif section == "Reports":
    st.title("Reports")
    with get_session() as s:
        active_contracts = s.exec(select(Contract).where(Contract.status.in_(["Draft","Assigned","In Progress","Submitted"])).order_by(Contract.due_date)).all()
        completed_tasks = s.exec(select(Task).where(Task.status=="Done").order_by(Task.completed_at.desc())).all()
        all_contracts = s.exec(select(Contract)).all()
        all_tasks = s.exec(select(Task)).all()

    st.subheader("All Active Contracts")
    df_active = pd.DataFrame([as_dict(c) for c in active_contracts])
    st.dataframe(df_active, use_container_width=True)
    st.download_button("Download Active Contracts (CSV)", df_active.to_csv(index=False).encode("utf-8"), "active_contracts.csv", "text/csv")

    st.subheader("All Completed Work (Tasks Done)")
    df_done = pd.DataFrame([as_dict(t) for t in completed_tasks])
    st.dataframe(df_done, use_container_width=True)
    st.download_button("Download Completed Tasks (CSV)", df_done.to_csv(index=False).encode("utf-8"), "completed_tasks.csv", "text/csv")

    st.subheader("Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Contracts (total)", len(all_contracts))
    col2.metric("Active Contracts", len(df_active))
    col3.metric("Tasks (total)", len(all_tasks))

# --- Audit Log ---
elif section == "Audit Log":
    if current_user.role != "admin":
        st.error("Admin only.")
        st.stop()
    st.title("Audit Log")
    with get_session() as s:
        logs = s.exec(select(AuditLog).order_by(AuditLog.at.desc()).limit(1000)).all()
    if logs:
        df = pd.DataFrame([as_dict(l) for l in logs])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No audit entries yet.")

# --- Admin ---
elif section == "Admin":
    if current_user.role != "admin":
        st.error("Admin only."); st.stop()
    st.title("Admin")
    st.subheader("Users")
    with get_session() as s:
        users = s.exec(select(User).order_by(User.created_at.desc())).all()
    st.dataframe(pd.DataFrame([as_dict(u) for u in users]), use_container_width=True)

    st.subheader("Add User")
    with st.form("add_user", clear_on_submit=True):
        name = st.text_input("Name")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["admin","officer","viewer"], index=1)
        active = st.checkbox("Active", value=True)
        submitted = st.form_submit_button("Create User")
        if submitted:
            with get_session() as s:
                u = User(name=name.strip(), email=email.strip(), role=role, active=active)
                s.add(u); s.commit()
                st.success(f"Created user {name} ({role})")
