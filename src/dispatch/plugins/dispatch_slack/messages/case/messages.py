from blockkit import Actions, Button, Context, Divider, Message, Section

from dispatch.config import DISPATCH_UI_URL
from dispatch.case.models import Case


def new_case_created_message(case: Case) -> Message:
    """Creates the slack json required for the new case message."""
    blocks = [
        Section(
            text="*New Case*\n A new case has been created, if you believe that or you are able to resolve please do so or contact the assignee.",
            accessory=Button(
                text="View",
                value="click_me_123",
                url=f"{DISPATCH_UI_URL}/{case.project.organization.slug}/cases/{case.name}",
                action_id="button-action",
            ),
        ),
        Section(
            text=f"*Assignee*\n <{case.assignee}|{case.assignee}>",
            accessory=Button(
                text="Take Ownership", value="click_me_123", action_id="button-action"
            ),
        ),
        Divider(),
        Section(text=f"*Title* \n {case.title}."),
        Section(
            text=f"*Description* \n {case.description} Additional information is available in the <{case.case_document.weblink}|case document>."
        ),
        Section(
            fields=[
                f"*Severity* \n {case.severity.name}",
                f"*Type* \n {case.case_type.name}",
                f"*Priority* \n {case.case_priority.name}",
            ]
        ),
    ]

    if case.signals:
        blocks.extend(
            [
                Divider(),
                Context(elements=["*Signal Details*"]),
                Section(
                    fields=[
                        "*Identity* \n <https://google.com|Kevin Glisson (Security Operations)>",
                        "*Action* \n Delete",
                        "*Account Name* \n DMZ",
                    ]
                ),
            ]
        )

    # always add actions
    blocks.extend(
        [
            Divider(),
            Actions(
                elements=[
                    Button(text="Resolve", action_id="foo", style="primary"),
                    Button(text="Escalate", action_id="foo", style="danger"),
                ]
            ),
        ]
    )

    return Message(blocks=blocks)
