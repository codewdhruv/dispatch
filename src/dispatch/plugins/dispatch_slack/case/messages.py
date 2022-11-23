import logging
from blockkit import (
    Actions,
    Button,
    Context,
    Divider,
    Message,
    Section,
    UsersSelect,
    MarkdownText,
    Modal,
)

from typing import Optional
from pydantic import BaseModel

from dispatch.database.core import engine, sessionmaker, SessionLocal
from dispatch.case import service as case_service
from dispatch.config import DISPATCH_UI_URL
from dispatch.enums import DispatchEnum
from dispatch.case.models import Case
from dispatch.organization import service as organization_service
from dispatch.conversation import service as conversation_service

from dispatch.plugins.dispatch_slack.fields import (
    DefaultBlockIds,
    title_input,
    description_input,
    project_select,
    incident_priority_select,
    incident_type_select,
    resolution_input,
    case_priority_select,
    case_type_select,
)

from dispatch.project import service as project_service
from dispatch.common.utils.cli import install_plugins

app = AsyncApp()

logging.basicConfig(level=logging.DEBUG)


class CaseNotificationActions(DispatchEnum):
    escalate = "case-notification-escalate"
    reassign = "case-notification-reassign"
    resolve = "case-notification-resolve"


class CaseResolveActions(DispatchEnum):
    submit = "case-notification-resolve-submit"


class CaseEscalateActions(DispatchEnum):
    submit = "case-notification-escalate-submit"
    project_select = "case-notification-escalate-project-select"


class CaseReportActions(DispatchEnum):
    submit = "case-report-submit"
    project_select = "case-report-project-select"


class CaseShortcutCallbacks(DispatchEnum):
    report = "case-report"


class SubjectMetadata(BaseModel):
    id: Optional[str]
    type: Optional[str]
    organization_slug: str
    project_id: Optional[str]
    channel_id: Optional[str]


def button_context_middleware(payload, context, next):
    """Attempt to determine the current context of the event."""
    context.update({"subject": SubjectMetadata.parse_raw(payload["value"])})
    next()


def action_context_middleware(body, context, next):
    """Attempt to determine the current context of the event."""
    context.update({"subject": SubjectMetadata.parse_raw(body["view"]["private_metadata"])})
    next()


def message_context_middleware(body, context, next):
    """Attemps to determine the current context of the event."""
    context.update({"subject": SubjectMetadata(**body["message"]["metadata"]["event_payload"])})
    next()


def slash_command_context_middleware(context, next):
    db_session = SessionLocal()
    organization_slugs = [o.slug for o in organization_service.get_all(db_session=db_session)]
    db_session.close()

    conversation = None
    for slug in organization_slugs:
        schema_engine = engine.execution_options(
            schema_translate_map={
                None: f"dispatch_organization_{slug}",
            }
        )

        scoped_db_session = sessionmaker(bind=schema_engine)()
        conversation = conversation_service.get_by_channel_id_ignoring_channel_type(
            db_session=scoped_db_session, channel_id=context["channel_id"]
        )
        if conversation:
            scoped_db_session.close()
            break

    context.update(
        {
            "subject": SubjectMetadata(
                type="incident",
                id=conversation.incident.id,
                organization_slug=conversation.project.organization.slug,
                project_id=conversation.project.id,
            )
        }
    )
    next()


def db_middleware(context, next):
    if not context.get("subject"):
        db_session = SessionLocal()
        slug = organization_service.get_default(db_session=db_session).slug
        context.update({"subject": SubjectMetadata(organization_slug=slug)})
        db_session.close()
    else:
        slug = context["subject"].organization_slug

    schema_engine = engine.execution_options(
        schema_translate_map={
            None: f"dispatch_organization_{slug}",
        }
    )
    context["db_session"] = sessionmaker(bind=schema_engine)()
    next()


def create_case_notification(case: Case, channel_id: str):
    blocks = [
        Context(elements=["*Case Details*"]),
        Section(
            text=f"*Title* \n {case.title}.",
            accessory=Button(
                text="View",
                url=f"{DISPATCH_UI_URL}/{case.project.organization.slug}/cases/{case.name}",
            ),
        ),
        Section(
            text=f"*Description* \n {case.description} Additional information is available in the <{case.case_document.weblink}|case document>."
        ),
        Section(
            text="*Assignee*",
            accessory=UsersSelect(
                initial_user=case.assignee.email,
                placeholder="Select Assignee",
                action_id=CaseNotificationActions.reassign,
            ),
        ),
        Section(
            fields=[
                f"*Severity* \n {case.case_severity.name}",
                f"*Type* \n {case.case_type.name}",
                f"*Priority* \n {case.case_priority.name}",
            ]
        ),
    ]

    if case.signal_instances:
        blocks.extend(
            [
                Divider(),
                Context(elements=["*Signal Details*"]),
            ]
        )
        for s in case.signal_instances:
            fields = []
            # TODO filter for only *important* 10 fields
            # TODO hide duplicates
            for k, v in s.raw.items():
                fields.append(f"*{k.strip()}* \n {v.strip()}")

            blocks.extend(
                [
                    Section(fields=fields[:10]),
                    Divider(),
                ]
            )

    button_metadata = SubjectMetadata(
        type="case",
        organization_slug=case.project.organization.slug,
        id=case.id,
        project_id=case.project.id,
        channel_id=channel_id,
    ).json()

    # always add actions
    blocks.extend(
        [
            Actions(
                elements=[
                    Button(
                        text="Resolve",
                        action_id=CaseNotificationActions.resolve,
                        style="primary",
                        value=button_metadata,
                    ),
                    Button(
                        text="Escalate",
                        action_id=CaseNotificationActions.escalate,
                        style="danger",
                        value=button_metadata,
                    ),
                ]
            ),
        ]
    )

    return Message(blocks=blocks).build()["blocks"]


@app.message("hello")
def message_hello(client, context):
    from dispatch.plugins.dispatch_slack.decorators import get_default_organization_scope

    install_plugins()
    db_session = get_default_organization_scope()
    case = db_session.query(Case).first()

    result = client.chat_postMessage(
        blocks=create_case_notification(case=case, channel_id=context["channel_id"]),
        channel=context["channel_id"],
        metadata={
            "event_type": "case_created",
            "event_payload": SubjectMetadata(
                type="case",
                id=case.id,
                organization_slug=case.project.organization.slug,
                project_id=case.project.id,
                channel_id=context["channel_id"],
            ).json(),
        },
    )

    client.chat_postMessage(
        text="All real-time case collaboration should be captured in this thread.",
        channel=context["channel_id"],
        thread_ts=result["ts"],
    )

    return result["ts"]


@app.action(CaseNotificationActions.escalate, middleware=[button_context_middleware, db_middleware])
def escalate_button_click(ack, body, say, client, db_session, context):
    ack()
    case = case_service.get(db_session=db_session, case_id=context["subject"].id)
    blocks = [
        Context(elements=[MarkdownText(text="Accept the defaults or adjust as needed.")]),
        title_input(initial_value=case.title),
        description_input(initial_value=case.description),
        project_select(
            db_session=db_session,
            initial_option=case.project.name,
            action_id=CaseEscalateActions.project_select,
            dispatch_action=True,
        ),
        incident_type_select(
            db_session=db_session,
            initial_option=case.case_type.incident_type.name,
            project_id=case.project.id,
        ),
        incident_priority_select(db_session=db_session, project_id=case.project.id, optional=True),
    ]

    modal = Modal(
        title="Escalate Case",
        blocks=blocks,
        submit="Escalate",
        close="Close",
        callback_id=CaseEscalateActions.submit,
        private_metadata=context["subject"].json(),
    ).build()
    client.views_open(trigger_id=body["trigger_id"], view=modal)


@app.action(
    CaseEscalateActions.project_select, middleware=[action_context_middleware, db_middleware]
)
def handle_project_select_action(ack, body, db_session, context, client):
    ack()
    values = body["view"]["state"]["values"]

    selected_project_name = values[DefaultBlockIds.project_select][
        CaseEscalateActions.project_select
    ]["selected_option"]["value"]

    project = project_service.get_by_name(
        db_session=db_session,
        name=selected_project_name,
    )

    blocks = [
        Context(elements=[MarkdownText(text="Accept the defaults or adjust as needed.")]),
        title_input(),
        description_input(),
        project_select(
            db_session=db_session,
            initial_option=selected_project_name,
            action_id=CaseEscalateActions.project_select,
            dispatch_action=True,
        ),
        incident_type_select(
            db_session=db_session, initial_option=None, project_id=project.id, block_id=None
        ),
        incident_priority_select(
            db_session=db_session,
            project_id=project.id,
            initial_option=None,
            optional=True,
            block_id=None,  # ensures state is reset
        ),
    ]

    modal = Modal(
        title="Escalate Case",
        blocks=blocks,
        submit="Submit",
        close="Close",
        callback_id=CaseEscalateActions.submit,
        private_metadata=context["subject"].json(),
    ).build()

    client.views_update(
        view_id=body["view"]["id"],
        hash=body["view"]["hash"],
        trigger_id=body["trigger_id"],
        view=modal,
    )


@app.view(CaseEscalateActions.submit, middleware=[action_context_middleware, db_middleware])
def handle_escalation_submission_event(ack, context, db_session, client, logger):
    ack()
    case = case_service.get(db_session=db_session, case_id=context["subject"].id)
    blocks = create_case_notification(case=case, channel_id=context["subject"].channel_id)
    client.chat_update(
        blocks=blocks, ts=case.conversation.thread_id, channel=case.conversation.channel_id
    )


@app.action(CaseNotificationActions.resolve, middleware=[button_context_middleware, db_middleware])
def resolve_button_click(ack, body, db_session, context, client):
    ack()
    case = case_service.get(db_session=db_session, case_id=context["subject"].id)

    blocks = [
        Context(elements=[MarkdownText(text="Accept the defaults or adjust as needed.")]),
        title_input(initial_value=case.title),
        description_input(initial_value=case.description),
        resolution_input(),
        case_type_select(
            db_session=db_session,
            initial_option=case.case_type.name,
            project_id=case.project.id,
        ),
        case_priority_select(db_session=db_session, project_id=case.project.id, optional=True),
    ]

    modal = Modal(
        title="Resolve Case",
        blocks=blocks,
        submit="Save",
        close="Close",
        callback_id=CaseResolveActions.submit,
        private_metadata=context["subject"].json(),
    ).build()
    client.views_open(trigger_id=body["trigger_id"], view=modal)


@app.view(CaseResolveActions.submit, middleware=[action_context_middleware, db_middleware])
def handle_resolve_submission_event(ack, context, db_session, client):
    ack()
    case = case_service.get(db_session=db_session, case_id=context["subject"].id)
    blocks = create_case_notification(case=case, channel_id=context["subject"].channel_id)
    client.chat_update(
        blocks=blocks, ts=case.conversation.thread_id, channel=case.conversation.channel_id
    )


@app.action(
    CaseNotificationActions.reassign, middleware=[message_context_middleware, db_middleware]
)
def handle_reassign_action(ack, body, context, db_session, logger):
    ack()
    logger.info(body)


@app.shortcut(CaseShortcutCallbacks.report, middleware=[db_middleware])
def report_issue(ack, shortcut, body, context, db_session, client):
    ack()
    initial_description = None
    if body.get("message"):
        initial_description = body["message"]["text"]

    blocks = [
        Context(
            elements=[
                MarkdownText(text="Fill the following form out to the best of your abilities.")
            ]
        ),
        title_input(),
        description_input(initial_value=initial_description),
        project_select(
            db_session=db_session,
            action_id=CaseReportActions.project_select,
            dispatch_action=True,
        ),
    ]

    modal = Modal(
        title="Report Issue",
        blocks=blocks,
        submit="Report",
        close="Close",
        callback_id=CaseReportActions.submit,
    ).build()
    client.views_open(trigger_id=shortcut["trigger_id"], view=modal)


@app.action(CaseReportActions.project_select, middleware=[db_middleware])
def handle_report_project_select_action(ack, body, db_session, context, client):
    ack()
    values = body["view"]["state"]["values"]

    selected_project_name = values[DefaultBlockIds.project_select][
        CaseReportActions.project_select
    ]["selected_option"]["value"]

    project = project_service.get_by_name(
        db_session=db_session,
        name=selected_project_name,
    )

    blocks = [
        Context(elements=[MarkdownText(text="Accept the defaults or adjust as needed.")]),
        title_input(),
        description_input(),
        project_select(
            db_session=db_session,
            initial_option=selected_project_name,
            action_id=CaseEscalateActions.project_select,
            dispatch_action=True,
        ),
        incident_type_select(
            db_session=db_session, initial_option=None, project_id=project.id, block_id=None
        ),
        incident_priority_select(
            db_session=db_session,
            project_id=project.id,
            initial_option=None,
            optional=True,
            block_id=None,  # ensures state is reset
        ),
    ]

    modal = Modal(
        title="Report Issue",
        blocks=blocks,
        submit="Report",
        close="Close",
        callback_id=CaseReportActions.submit,
        private_metadata=context["subject"].json(),
    ).build()

    client.views_update(
        view_id=body["view"]["id"],
        hash=body["view"]["hash"],
        trigger_id=body["trigger_id"],
        view=modal,
    )


@app.view(CaseReportActions.submit, middleware=[db_middleware])
def handle_report_submission_event(ack, body, context, db_session, client, logger):
    ack()

    # create the case

    # @ the user in the case thread as confirmation
