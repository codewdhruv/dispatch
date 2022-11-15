"""
.. module: dispatch.case.messaging
    :platform: Unix
    :copyright: (c) 2019 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
"""
import logging

from dispatch.config import DISPATCH_UI_URL
from dispatch.database.core import SessionLocal
from dispatch.case.models import Case, CaseRead
from dispatch.notification import service as notification_service
from dispatch.messaging.strings import (
    CASE_NOTIFICATION,
    MessageType,
)


log = logging.getLogger(__name__)


def send_case_created_notifications(case: Case, db_session: SessionLocal):
    """Sends case created notifications."""
    notification_template = CASE_NOTIFICATION.copy()

    case_description = (
        case.description if len(case.description) <= 500 else f"{case.description[:500]}..."
    )

    notification_kwargs = {
        "name": case.name,
        "status": case.status,
        "type": case.case_type.name,
        "description": case_description,
        "severity": case.case_severity.name,
        "severity_description": case.case_severity.description,
        "priority": case.case_priority.name,
        "priority_description": case.case_priority.description,
        "assignee": case.assignee,
        "case_id": case.id,
        "case_url": f"{DISPATCH_UI_URL}/{case.project.organization.slug}/cases/{case.name}",
        "organization_slug": case.project.organization.slug,
    }

    notification_params = {
        "text": "Case Notification",
        "type": MessageType.case_notification,
        "template": notification_template,
        "kwargs": notification_kwargs,
    }

    notification_service.filter_and_send(
        db_session=db_session,
        project_id=case.project.id,
        class_instance=case,
        notification_params=notification_params,
    )

    log.debug("Case created notifications sent.")


def send_case_update_notifications(case: Case, previous_case: CaseRead, db_session=SessionLocal):
    """Creates and send case update notifications."""
    pass


def create_case_thread(case: Case, db_session=SessionLocal):
    """Creates a thread based on the creation notification."""
    pass


def update_case_notification(case: Case, previous_case: CaseRead, db_session=SessionLocal):
    """Sends notifications about case changes"""
    pass
