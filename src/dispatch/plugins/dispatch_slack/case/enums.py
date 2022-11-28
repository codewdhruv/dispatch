from dispatch.enums import DispatchEnum


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
