from dispatch.case.models import Case
from dispatch.case.messaging import send_case_created_notifications
from dispatch.database import SessionLocal

db_session = SessionLocal()
case = db_session.query(Case).one()
send_case_created_notifications(case, db_session)
