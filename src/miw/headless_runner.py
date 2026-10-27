"""Bounded helper and semantic-application execution without a visible console.

This is a local consumer-owned realization of a HeadlessRunner surface.  It is
not a UGK certification, a sandbox, or authority to execute arbitrary commands.
"""
from __future__ import annotations

from collections.abc import Sequence
import os
from pathlib import Path
import subprocess
from typing import Any

from .common import BOUNDARY, Refusal, read_json, require, seal


class HeadlessRunner:
    """Run an already-admitted argv without shell interpretation or a console."""

    def run(self, args: Sequence[str | os.PathLike[str]], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        require(type(args) in (list, tuple) and len(args) > 0, "HEADLESS_ARGV_REQUIRED")
        require(not kwargs.pop("shell", False), "HEADLESS_SHELL_FORBIDDEN")
        argv = [str(item) for item in args]
        require(all(item and "\x00" not in item for item in argv), "HEADLESS_ARGV_INVALID")
        if os.name == "nt":
            kwargs["creationflags"] = int(kwargs.get("creationflags", 0)) | subprocess.CREATE_NO_WINDOW
            startup = kwargs.get("startupinfo") or subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = startup
        return subprocess.run(argv, shell=False, **kwargs)


HEADLESS_RUNNER = HeadlessRunner()


def run_headless(args: Sequence[str | os.PathLike[str]], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
    return HEADLESS_RUNNER.run(args, **kwargs)


def application_court(dossier: Path, bindings: Path | None = None) -> dict[str, Any]:
    """Exercise the actual Mosaic semantic tree and bounded controller flow."""
    from .foundry_view import VIEWS, make_headless, payload
    from .workbench import build_workspace

    dossier = Path(dossier)
    ui = make_headless(dossier)
    controller = ui.miw_controller
    projections = []
    for view in VIEWS:
        ui.apply({"intent": "ACTIVATE", "node_id": "nav_" + view})
        require(ui.state["active_view"] == view, "HEADLESS_VIEW_PROJECTION_FAILED", detail=view)
        projections.append(view)

    controller.dispatch({"intent": "ACTIVATE", "node_id": "nav_workbench"})
    controller.dispatch({"intent": "ACTIVATE", "node_id": "workbench_validate"})
    require(ui.state["status"] == "WORKSPACE VALIDATED", "HEADLESS_WORKSPACE_VALIDATION_FAILED")
    if bindings is not None:
        controller.workspace = build_workspace(dossier, read_json(Path(bindings)))

    controller.dispatch({"intent": "ACTIVATE", "node_id": "workbench_explain"})
    explain_status = ui.state["status"]
    controller.dispatch({"intent": "TEXT_COMMIT", "node_id": "workbench_lane", "value": "PROOF_RECHECK"})
    controller.dispatch({"intent": "ACTIVATE", "node_id": "workbench_lower"})
    lower_status = ui.state["status"]
    controller.dispatch({"intent": "ACTIVATE", "node_id": "workbench_run"})
    run_status = ui.state["status"]
    controller.dispatch({"intent": "ACTIVATE", "node_id": "workbench_bind"})
    bind_status = ui.state["status"]

    require(explain_status == "OBLIGATION EXPLAINED", "HEADLESS_EXPLAIN_FAILED")
    require(lower_status == "LOWERED BOUNDED", "HEADLESS_LOWER_FAILED")
    require(run_status == "LOCAL CHECK CHECKED_SOURCE_PROOF", "HEADLESS_LOCAL_CHECK_FAILED")
    require(bind_status == "BINDING PROPOSED | NOT ADOPTED", "HEADLESS_BINDING_BOUNDARY_FAILED")
    tree = payload()
    return seal({
        "schema": "miw.headless-application-court.v1", **BOUNDARY,
        "status": "PASSED_HEADLESS_APPLICATION_COURT",
        "views_exercised": projections,
        "semantic_node_count": len(tree["application"]["tree"]["children"]),
        "operation_count": len(tree["application"]["declared_operation_ids"]),
        "workbench_flow": {
            "explain": explain_status, "lower": lower_status,
            "run": run_status, "binding": bind_status,
        },
        "native_window_execution": "NOT_ESTABLISHED_BY_HEADLESS_RUNNER",
        "external_effects": "NONE",
        "claim_ceiling": "Semantic application/controller execution only; no HWND, visual, external-effect, or production claim.",
    }, "court_root")


__all__ = ["HEADLESS_RUNNER", "HeadlessRunner", "application_court", "run_headless"]
