from blockkit import (
    Actions,
    Button,
    Context,
    Divider,
    Message,
    Section,
)

from dispatch.config import DISPATCH_UI_URL
from dispatch.case.enums import CaseStatus
from dispatch.case.models import Case
from dispatch.plugins.dispatch_slack.models import SubjectMetadata
from dispatch.plugins.dispatch_slack.case.enums import (
    CaseNotificationActions,
)


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
            text=f"*Description* \n {case.description} \n \n Additional information is available in the <{case.case_document.weblink}|case document>."
        ),
        Section(
            fields=[
                f"*Assignee* \n {case.assignee.email}",
                f"*Status* \n {case.status}",
                f"*Severity* \n {case.case_severity.name}",
                f"*Type* \n {case.case_type.name}",
                f"*Priority* \n {case.case_priority.name}",
            ]
        ),
    ]

    button_metadata = SubjectMetadata(
        type="case",
        organization_slug=case.project.organization.slug,
        id=case.id,
        project_id=case.project.id,
        channel_id=channel_id,
    ).json()

    if case.status == CaseStatus.escalated:
        blocks.extend(
            [
                Actions(
                    elements=[
                        Button(
                            text="Join Incident",
                            action_id=CaseNotificationActions.join_incident,
                            style="primary",
                            value=button_metadata,
                        )
                    ]
                )
            ]
        )

    elif case.status == CaseStatus.closed:
        blocks.extend(
            [
                Actions(
                    elements=[
                        Button(
                            text="Re-open",
                            action_id=CaseNotificationActions.reopen,
                            style="primary",
                            value=button_metadata,
                        )
                    ]
                )
            ]
        )
    else:
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
        blocks.extend(
            [
                Actions(
                    elements=[
                        Button(
                            text="Edit",
                            action_id=CaseNotificationActions.edit,
                            style="primary",
                            value=button_metadata,
                        ),
                        Button(
                            text="Acknowledge",
                            action_id=CaseNotificationActions.acknowledge,
                            style="primary",
                            value=button_metadata,
                        ),
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
                )
            ]
        )

    return Message(blocks=blocks).build()["blocks"]
