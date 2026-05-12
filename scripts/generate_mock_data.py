from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("regguard.mock_data")

MOCK_DIR = Path("mock_data")


def _fallback_matrix() -> Dict[str, Any]:
    """Return a fallback gap matrix structure when compute_gap_matrix fails."""

    path = MOCK_DIR / "gap_matrix_C1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    """Generate or refresh mock gap matrix data."""

    MOCK_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from gap.engine import compute_gap_matrix  # type: ignore

        import asyncio

        matrix = asyncio.run(
            compute_gap_matrix(
                ["C1_lendingkart_fpc_2025"],
                ["R1_digital_lending_directions_2025", "R2_kyc_master_direction_2025"],
            )
        )
        data = matrix.dict() if hasattr(matrix, "dict") else matrix
        (MOCK_DIR / "gap_matrix_C1.json").write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("Saved computed gap matrix to mock_data/gap_matrix_C1.json")
        return
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falling back to mock data: %s", exc)

    data = _fallback_matrix()
    (MOCK_DIR / "gap_matrix_C1.json").write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Saved fallback gap matrix to mock_data/gap_matrix_C1.json")


if __name__ == "__main__":
    main()
