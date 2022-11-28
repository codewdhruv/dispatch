from blockkit import (
    Context,
    MarkdownText,
    Modal,
)

from dispatch.case import service as case_service
from dispatch.case.models import Case
from dispatch.project import service as project_service
from dispatch.common.utils.cli import install_plugins

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

from dispatch.plugins.dispatch_slack.models import SubjectMetadata

from dispatch.plugins.dispatch_slack.case.enums import (
    CaseEscalateActions,
    CaseNotificationActions,
    CaseResolveActions,
    CaseReportActions,
    CaseShortcutCallbacks,
)

from dispatch.plugins.dispatch_slack.bolt import (
    app,
    action_context_middleware,
    db_middleware,
    button_context_middleware,
    message_context_middleware,
)


# @app.message("hello")
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
