from __future__ import annotations

from pathlib import Path

import resend

from config import RESEND_API_KEY


def send_report_email(from_email: str, to_email: str, subject: str, body: str, pdf_path: Path) -> None:
    """Send the PDF report via Resend."""

    resend.api_key = RESEND_API_KEY
    with pdf_path.open("rb") as handle:
        resend.Emails.send(
            {
                "from": from_email,
                "to": to_email,
                "subject": subject,
                "html": body,
                "attachments": [
                    {
                        "filename": pdf_path.name,
                        "content": handle.read(),
                    }
                ],
            }
        )
