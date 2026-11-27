import io
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def build_dossier_pdf(dossier_data: dict[str, Any]) -> bytes:
    """Render a consumer evidence dossier into PDF bytes using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Hisaab Evidence Dossier")
    styles = getSampleStyleSheet()
    story: list[Any] = []

    story.append(Paragraph("Hisaab — Evidence Dossier", styles["Title"]))
    story.append(Spacer(1, 12))

    promise = dossier_data["promise"]
    amount_paise = promise.get("amount_paise")
    amount_str = f"Rs. {amount_paise / 100:,.2f}" if amount_paise is not None else "N/A"

    details = [
        f"<b>Promise ID:</b> {promise['promise_id']}",
        f"<b>Merchant:</b> {promise['merchant_name']}",
        f"<b>Category:</b> {promise.get('category') or 'other'}",
        f"<b>Promised Amount:</b> {amount_str}",
        f"<b>Due Date:</b> {promise.get('due_date') or 'N/A'}",
        f"<b>Status:</b> {promise['status']}",
    ]
    for line in details:
        story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Exact Promise Quote", styles["Heading2"]))
    story.append(Paragraph(f'"{promise["exact_quote"]}"', styles["Italic"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Timeline of Events", styles["Heading2"]))
    for event in dossier_data.get("timeline", []):
        story.append(
            Paragraph(
                f"• [{event['occurred_at']}] <b>{event['type']}</b>: {event['description']}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Escalation History", styles["Heading2"]))
    steps = dossier_data.get("escalation_steps", [])
    if not steps:
        story.append(Paragraph("No escalation steps recorded yet.", styles["Normal"]))
    else:
        for step in steps:
            story.append(
                Paragraph(
                    f"• Rung {step['rung']} ({step['notice_type']}) — Deadline: {step['deadline']}",
                    styles["Normal"],
                )
            )

    story.append(Spacer(1, 16))
    story.append(Paragraph(dossier_data["not_legal_advice_notice"], styles["Italic"]))

    doc.build(story)
    return buffer.getvalue()
