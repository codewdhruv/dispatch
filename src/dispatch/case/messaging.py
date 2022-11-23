"""
.. module: dispatch.case.messaging
    :platform: Unix
    :copyright: (c) 2019 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
"""
import logging


from dispatch.database.core import SessionLocal
from dispatch.case.models import Case, CaseRead
from dispatch.messaging.strings import MessageType
from dispatch.notification import service as notification_service


log = logging.getLogger(__name__)


def send_case_created_notifications(case: Case, db_session: SessionLocal):
    """Sends case created notifications."""
    notification_params = {
        "text": "Case Created",
        "template": [],
        "items": [],
        "type": MessageType.case_created_notification,
        "kwargs": {"case": case},
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
