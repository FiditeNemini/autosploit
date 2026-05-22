#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_VIEW = ROOT / "ExploitBot" / "Sources" / "ExploitBot" / "Views" / "Tabs" / "ReportTabView.swift"
CONTENT_VIEW = ROOT / "ExploitBot" / "Sources" / "ExploitBot" / "Views" / "ContentView.swift"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run() -> None:
    report = REPORT_VIEW.read_text(encoding="utf-8")
    content = CONTENT_VIEW.read_text(encoding="utf-8")

    require("var onDeleteFinding: ((UUID) -> Void)?" in report, "ReportTabView is missing onDeleteFinding callback")
    require("Button(action: { onDeleteFinding?(f.id) })" in report, "Report finding delete button does not use callback")
    require("findingService.delete(id: f.id)" not in report, "Report finding delete button still bypasses AppState")
    require("onDeleteFinding: { id in state.deleteReportFinding(id: id) }" in content, "ContentView does not route report delete to AppState")

    print("report-visible-delete-wiring proof passed")


if __name__ == "__main__":
    try:
        run()
    except AssertionError as exc:
        print(f"report-visible-delete-wiring proof failed: {exc}", flush=True)
        raise SystemExit(1)
