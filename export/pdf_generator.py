from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from weasyprint import HTML

TEMPLATE_PATH = Path("export/templates/report.html")


def generate_report_pdf(data: Dict[str, Any], output_path: Path) -> None:
    """Generate a PDF report from gap matrix data."""

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    rows_html = ""
    for clause in data.get("clauses", []):
        rows_html += (
            "<tr>"
            f"<td>{clause.get('clause_number', '')}</td>"
            f"<td>{clause.get('section', '')}</td>"
            f"<td>{clause.get('status', '')}</td>"
            f"<td>{clause.get('confidence', '')}</td>"
            f"<td>{clause.get('regulatory_citation', '')} {clause.get('company_citation', '')}</td>"
            "</tr>"
        )

    html = template.format(
        company_name=data.get("company_name", ""),
        overall_score=data.get("overall_score", ""),
        rows=rows_html,
    )

    HTML(string=html).write_pdf(str(output_path))
