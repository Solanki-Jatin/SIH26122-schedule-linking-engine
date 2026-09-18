"""
Layer 1: Data capture.

Ingests heterogeneous field inputs and normalizes them into a common
RawReport shape before they go to layer 3 for linking. Per the PS,
the prototype targets 2-3 input formats, not full OCR/ASR:

  1. Structured CSV/form: task_id already known, direct pass-through.
  2. Free-text report: a one-line supervisor note, no task_id, needs
     fuzzy linking in layer 3.
  3. (voice input is captured client-side via Web Speech API in the
     frontend demo and arrives here as free text, so it reuses path 2)

This module deliberately does not attempt discipline classification or
entity extraction beyond simple parsing. Any semantic work is layer 3's
job, kept separate so linking logic is testable independently of intake
format.
"""

import csv
from dataclasses import dataclass
from datetime import date
from io import StringIO


@dataclass
class RawReport:
    """Normalized shape all intake paths converge to before linking."""

    raw_text: str
    report_date: date
    reported_by: str | None = None
    known_task_id: str | None = None  # set only when the source already
    # supplies a plan task_id (e.g. a structured CSV export); free-text
    # and voice reports leave this None for layer 3 to resolve.
    percent_complete: float | None = None


def parse_csv_reports(csv_text: str) -> list[RawReport]:
    """
    Parses a structured CSV report, expected columns:
    task_id, description, report_date (YYYY-MM-DD), percent_complete, reported_by

    task_id is trusted directly, no fuzzy linking needed for these rows.
    Used for the 'discipline-wise spreadsheet' input format from the PS.
    """
    reader = csv.DictReader(StringIO(csv_text))
    reports = []
    for row in reader:
        reports.append(
            RawReport(
                raw_text=row["description"],
                report_date=date.fromisoformat(row["report_date"]),
                reported_by=row.get("reported_by") or None,
                known_task_id=row.get("task_id") or None,
                percent_complete=(
                    float(row["percent_complete"])
                    if row.get("percent_complete")
                    else None
                ),
            )
        )
    return reports


def parse_free_text_report(
    text: str, report_date: date, reported_by: str | None = None
) -> RawReport:
    """
    Parses one free-text supervisor note (typed or voice-transcribed).
    No task_id is known yet, layer 3 must resolve it via fuzzy match.
    Used for the 'verbal supervisor update' / 'daily progress report'
    input formats from the PS.
    """
    return RawReport(
        raw_text=text.strip(),
        report_date=report_date,
        reported_by=reported_by,
        known_task_id=None,
        percent_complete=None,
    )
