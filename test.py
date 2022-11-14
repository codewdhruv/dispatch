from dispatch.plugins.dispatch_slack.decorators import get_organization_scope_from_slug

from dispatch.case.models import Case
from dispatch.case.messaging import send_case_created_notifications

db_session = get_organization_scope_from_slug("default")
case = db_session.query(Case).first()
send_case_created_notifications(case, db_session)
