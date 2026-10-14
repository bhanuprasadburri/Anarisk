"""Case-workflow notification helpers built on services.notifications.

SCOPE / WIRING NOTE
-------------------
app/services/cases.py and app/api/v1/cases.py are owned by another workstream and
MUST NOT be edited from this module. The helpers below are the single place where
case lifecycle -> notification mapping lives, so they can be wired in from the
case workflow with one import + one call per event:

    # in app/services/cases.py (owner of that file decides placement):
    from app.services import case_notify

    case_notify.on_case_created(db, case)                        # after create_case flush
    case_notify.on_case_assigned(db, case, assignee.id)          # inside assign()
    case_notify.on_case_status(db, case, data.status)            # inside change_status()
    case_notify.on_case_escalated(db, case)                      # inside escalate()

Contract (same as every notify() caller in services/notifications.py):
  * these helpers only ADD rows to the caller's current transaction - they never
    commit and never raise, so they can never break the case flow;
  * call them BEFORE the workflow's db.commit(), or commit afterwards.

CURRENT STATE (verified by grep on 2026-10-13): services/cases.py already calls
notifications directly for case_created, case_assigned, case_escalated and
case_resolved, so wiring these helpers as well would DUPLICATE those messages.
Do not wire on_case_created / on_case_assigned / on_case_escalated alongside the
existing calls without de-duplicating first; on_case_status (generic status-change
notifications for non-resolve transitions) is the one that is not yet covered.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import InvestigationCase
from app.models.enums import CaseStatus
from app.services import notifications as notify_svc

STATUS_LABELS = {s.value: s.value.replace("_", " ") for s in CaseStatus}


def _case_url(case: InvestigationCase) -> str:
    return f"/cases/{case.id}"


def _recipients(db: Session, case: InvestigationCase, *, include_admins: bool = True) -> list[uuid.UUID]:
    """Creator + current assignee (+ administrators by default), de-duplicated."""
    ids: list[uuid.UUID] = []
    if case.created_by_id:
        ids.append(case.created_by_id)
    if case.assigned_to_id:
        ids.append(case.assigned_to_id)
    if include_admins:
        ids.extend(notify_svc.admins(db))
    return ids


def on_case_created(db: Session, case: InvestigationCase) -> int:
    """New (typically unassigned) case: tell administrators it needs triage."""
    return notify_svc.notify(
        db, notify_svc.admins(db), "case_created",
        f"New case {case.case_number}",
        f"{case.severity.value} severity case '{case.title}' was created and needs triage.",
        link_url=_case_url(case), resource=("case", case.id), dedupe_hours=24,
    )


def on_case_assigned(db: Session, case: InvestigationCase, assignee_id: uuid.UUID) -> int:
    """Assignment / reassignment: tell the assignee the case is theirs."""
    return notify_svc.notify(
        db, [assignee_id], "case_assigned",
        f"Case {case.case_number} assigned to you",
        f"'{case.title}' ({case.severity.value}) is now assigned to you.",
        link_url=_case_url(case), resource=("case", case.id),
    )


def on_case_status(db: Session, case: InvestigationCase, to_status: CaseStatus | str) -> int:
    """Generic status change: notify creator + assignee (+ admins)."""
    status = to_status.value if isinstance(to_status, CaseStatus) else str(to_status)
    return notify_svc.notify(
        db, _recipients(db, case), "case_status_changed",
        f"Case {case.case_number} is now {STATUS_LABELS.get(status, status)}",
        f"'{case.title}' moved to {STATUS_LABELS.get(status, status)}.",
        link_url=_case_url(case), resource=("case", case.id),
    )


def on_case_escalated(db: Session, case: InvestigationCase) -> int:
    """Escalation: administrators + the current owner must see the handoff."""
    return notify_svc.notify(
        db, _recipients(db, case), "case_escalated",
        f"Case {case.case_number} escalated",
        f"'{case.title}' was escalated{': ' + case.escalation_summary if case.escalation_summary else ''}.",
        link_url=_case_url(case), resource=("case", case.id),
    )
