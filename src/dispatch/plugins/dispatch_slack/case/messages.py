from blockkit import (
    Actions,
    Button,
    Context,
    Divider,
    Message,
    Section,
    UsersSelect,
)

from dispatch.config import DISPATCH_UI_URL
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
