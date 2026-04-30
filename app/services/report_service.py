"""Reporting utilities for run outputs (including Allure-compatible artifacts)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from uuid import uuid4

from app.models.execution_models import CaseExecutionResult, RunExecutionSummary


class ReportService:
    """Builds run report artifacts in deterministic run-local paths."""

    def write_allure_results(self, run_dir: Path, summary: RunExecutionSummary) -> Path:
        """Write minimal Allure-compatible result files under `<run_dir>/allure-results`."""
        allure_dir = run_dir / "allure-results"
        allure_dir.mkdir(parents=True, exist_ok=True)

        for case in summary.cases:
            self._write_case_result(allure_dir=allure_dir, run_id=summary.run_id, case=case)

        return allure_dir

    def _write_case_result(self, allure_dir: Path, run_id: str, case: CaseExecutionResult) -> None:
        result_uuid = uuid4().hex
        status = "passed" if case.status == "passed" else "failed"
        total_duration = sum(s.duration_ms for s in case.steps)
        steps: list[dict] = []
        attachments: list[dict] = []

        for step in case.steps:
            step_status = "passed" if step.status == "passed" else "failed"
            steps.append(
                {
                    "name": f"Step {step.step_index}: {step.raw_step}",
                    "status": step_status,
                    "statusDetails": (
                        {"message": step.error_message, "trace": step.error_message}
                        if step.error_message
                        else {}
                    ),
                    "stage": "finished",
                    "start": 0,
                    "stop": max(1, step.duration_ms),
                }
            )
            if step.screenshot_path:
                attachments.append(
                    {
                        "name": f"step-{step.step_index}-screenshot",
                        "source": Path(step.screenshot_path).name,
                        "type": "image/png",
                    }
                )
            if step.html_snapshot_path:
                attachments.append(
                    {
                        "name": f"step-{step.step_index}-html",
                        "source": Path(step.html_snapshot_path).name,
                        "type": "text/html",
                    }
                )

        payload = {
            "uuid": result_uuid,
            "historyId": f"{run_id}:{case.test_case_id}",
            "name": case.test_case_name or case.test_case_id,
            "fullName": f"{case.module}.{case.test_case_id}" if case.module else case.test_case_id,
            "status": status,
            "statusDetails": {},
            "stage": "finished",
            "steps": steps,
            "attachments": attachments,
            "labels": [
                {"name": "suite", "value": case.module or "default"},
                {"name": "testCaseId", "value": case.test_case_id},
                {"name": "runId", "value": run_id},
            ],
            "start": 0,
            "stop": max(1, total_duration),
        }
        (allure_dir / f"{result_uuid}-result.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def write_html_report(self, run_dir: Path, summary: RunExecutionSummary) -> Path:
        """Write a simple dashboard-style HTML report under `<run_dir>/report.html`."""
        report_path = run_dir / "report.html"
        report_path.write_text(self._build_html(summary), encoding="utf-8")
        return report_path

    def _build_html(self, summary: RunExecutionSummary) -> str:
        status_class = "ok" if summary.status == "completed" else "bad"
        case_blocks: list[str] = []
        for case in summary.cases:
            rows: list[str] = []
            for step in case.steps:
                shot_href = self._to_run_relative_href(step.screenshot_path)
                html_href = self._to_run_relative_href(step.html_snapshot_path)
                shot = (
                    f'<a href="{escape(shot_href)}" target="_blank">screenshot</a>'
                    if shot_href
                    else "-"
                )
                html = (
                    f'<a href="{escape(html_href)}" target="_blank">html</a>'
                    if html_href
                    else "-"
                )
                err = escape(step.error_message or "")
                rows.append(
                    f"""
                    <tr>
                      <td class="mono">{step.step_index}</td>
                      <td>{escape(step.raw_step)}</td>
                      <td><span class="pill {'ok' if step.status == 'passed' else 'bad'}">{escape(step.status)}</span></td>
                      <td><span class="mono">{escape(step.action or '')}</span></td>
                      <td>{escape(step.target or '')}</td>
                      <td class="mono">{step.duration_ms}</td>
                      <td class="url">{escape(step.url or '')}</td>
                      <td>{shot}</td>
                      <td>{html}</td>
                      <td class="err">{err}</td>
                    </tr>
                    """
                )
            case_blocks.append(
                f"""
                <section class="card">
                  <h3>{escape(case.test_case_id)} - {escape(case.test_case_name or '')}</h3>
                  <p class="meta">
                    <span>Module: <strong>{escape(case.module or '-')}</strong></span>
                    <span>Status: <span class="pill {'ok' if case.status == 'passed' else 'bad'}">{escape(case.status)}</span></span>
                  </p>
                  <div class="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Step</th>
                          <th>Status</th>
                          <th>Action</th>
                          <th>Target</th>
                          <th>ms</th>
                          <th>URL</th>
                          <th>Screenshot</th>
                          <th>HTML</th>
                          <th>Error</th>
                        </tr>
                      </thead>
                      <tbody>
                        {''.join(rows)}
                      </tbody>
                    </table>
                  </div>
                </section>
                """
            )

        return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Run Report {escape(summary.run_id)}</title>
  <style>
    :root {{
      --bg: #f3f6fb;
      --panel: #ffffff;
      --text: #111827;
      --muted: #6b7280;
      --line: #e5e7eb;
      --header: #f9fafb;
      --ok-bg: #dcfce7;
      --ok-text: #166534;
      --bad-bg: #fee2e2;
      --bad-text: #991b1b;
      --shadow: 0 6px 20px rgba(17, 24, 39, 0.06);
      --radius: 12px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.35;
    }}
    .container {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 24px;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 18px;
    }}
    .header h1 {{
      margin: 0;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: 0.2px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 12px;
      margin: 0 0 18px;
    }}
    .stat, .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}
    .stat {{
      padding: 14px;
    }}
    .stat .k {{
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .stat .v {{
      font-size: 24px;
      font-weight: 700;
      margin-top: 4px;
    }}
    .card {{
      padding: 16px;
      margin-bottom: 16px;
    }}
    .card h3 {{
      margin: 0 0 10px;
      font-size: 17px;
      font-weight: 650;
    }}
    .meta {{
      margin: 0 0 12px;
      color: var(--muted);
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.3px;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .ok {{ background: var(--ok-bg); color: var(--ok-text); }}
    .bad {{ background: var(--bad-bg); color: var(--bad-text); }}
    .table-wrap {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 10px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      min-width: 1100px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px 10px;
      vertical-align: top;
    }}
    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: var(--header);
      text-align: left;
      color: #374151;
      font-weight: 650;
    }}
    tr:hover td {{
      background: #fbfdff;
    }}
    .mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .url {{
      max-width: 280px;
      word-break: break-word;
      color: #334155;
    }}
    .err {{
      max-width: 360px;
      white-space: pre-wrap;
      color: #7f1d1d;
      word-break: break-word;
    }}
    a {{
      color: #2563eb;
      text-decoration: none;
      font-weight: 600;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    @media (max-width: 980px) {{
      .container {{ padding: 14px; }}
      .cards {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
      .header h1 {{ font-size: 19px; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Run Report - {escape(summary.run_id)}</h1>
      <span class="pill {status_class}">{escape(summary.status)}</span>
    </div>

    <div class="cards">
      <div class="stat"><div class="k">Total Cases</div><div class="v">{summary.total_cases}</div></div>
      <div class="stat"><div class="k">Passed</div><div class="v">{summary.passed_cases}</div></div>
      <div class="stat"><div class="k">Failed</div><div class="v">{summary.failed_cases}</div></div>
      <div class="stat"><div class="k">Skipped</div><div class="v">{summary.skipped_cases}</div></div>
      <div class="stat"><div class="k">Pending</div><div class="v">{summary.pending_cases}</div></div>
    </div>

    {''.join(case_blocks)}
  </div>
</body>
</html>
"""

    @staticmethod
    def _to_run_relative_href(path_value: str | None) -> str | None:
        """Convert stored artifact path to href relative to `<run_dir>/report.html`."""
        if not path_value:
            return None
        normalized = path_value.replace("\\", "/")
        for marker in ("/screenshots/", "/html/"):
            if marker in normalized:
                tail = normalized.split(marker, 1)[1]
                return f"{marker.strip('/')}/{tail}"
        if normalized.startswith("screenshots/") or normalized.startswith("html/"):
            return normalized
        return None

