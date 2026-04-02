"""QA review routes."""

import json
import os

from flask import Blueprint, render_template, request, redirect

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from shared.db import project_get, project_update, queue_remove

review_bp = Blueprint("review", __name__)


def _load_test_report(project_dir):
    """Load SDD test report for checklist generation."""
    report_path = os.path.join(project_dir, "sdd-output", "test-report.md")
    if os.path.exists(report_path):
        with open(report_path) as f:
            return f.read()
    return None


def _generate_checklist(test_report):
    """Generate QA checklist from test report + standard checks."""
    checklist = []

    # Standard manual checks
    checklist.extend([
        {"id": "responsive", "label": "App is responsive on mobile and desktop", "auto": False},
        {"id": "errors", "label": "Error states are handled gracefully", "auto": False},
        {"id": "navigation", "label": "All navigation links work correctly", "auto": False},
        {"id": "forms", "label": "Form submissions work and validate input", "auto": False},
        {"id": "data", "label": "Data persists correctly (create, read, update, delete)", "auto": False},
        {"id": "auth", "label": "Authentication flow works (if applicable)", "auto": False},
        {"id": "performance", "label": "Pages load within reasonable time", "auto": False},
    ])

    # Extract automated test results from report
    if test_report:
        for line in test_report.splitlines():
            line = line.strip()
            if line.startswith("- [x]"):
                checklist.append({"id": f"auto-{len(checklist)}", "label": line[5:].strip(), "auto": True, "passed": True})
            elif line.startswith("- [ ]"):
                checklist.append({"id": f"auto-{len(checklist)}", "label": line[5:].strip(), "auto": True, "passed": False})

    return checklist


@review_bp.route("/review/<slug>", methods=["GET"])
def show_review(slug):
    """Show QA review page for a project."""
    project = project_get(slug)
    if not project:
        return {"error": f"Project '{slug}' not found"}, 404

    test_report = _load_test_report(project["project_dir"])
    checklist = _generate_checklist(test_report)

    app_url = project.get("deployed_url", "")

    return render_template("review.html",
                           project=project,
                           checklist=checklist,
                           app_url=app_url)


@review_bp.route("/review/<slug>", methods=["POST"])
def submit_review(slug):
    """Process QA decision — promote or scrap."""
    project = project_get(slug)
    if not project:
        return {"error": f"Project '{slug}' not found"}, 404

    action = request.form.get("action")

    if action == "promote":
        project_update(slug, status="promoted")
    elif action == "scrap":
        project_update(slug, status="scrapped")
        queue_remove(project["id"])
    else:
        return {"error": "Invalid action"}, 400

    return render_template("review.html",
                           project=project,
                           checklist=[],
                           app_url="",
                           message=f"Project {slug} marked as {action}d")
