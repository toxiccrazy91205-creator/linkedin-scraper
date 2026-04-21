import os
import io
import csv
import json
from datetime import datetime
from pathlib import Path
from flask import Blueprint, jsonify, request, Response

from services import run_async_with_retry
from logger import app_logger

api_bp = Blueprint('api', __name__, url_prefix='/api')
SESSION_DIR = Path(__file__).parent / ".sessions"

# ---------------------------------------------------------------------------
# Global Error Handling
# ---------------------------------------------------------------------------

from werkzeug.exceptions import HTTPException

@api_bp.app_errorhandler(Exception)
def handle_global_exceptions(e):
    if isinstance(e, HTTPException):
        return e
        
    app_logger.error(f"Unhandled Exception: {str(e)}", exc_info=True)
    return jsonify({
        "status": "error",
        "error": "Internal Server Error",
        "message": str(e)
    }), 500


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@api_bp.route("/status", methods=["GET"])
def api_status():
    """Server health check and session status."""
    has_session = (SESSION_DIR / "linkedin.json").exists()
    return jsonify({
        "status": "online",
        "version": "2.0.0",
        "session_active": has_session,
        "timestamp": datetime.now().isoformat(),
        "capabilities": {
            "without_login": ["search_jobs", "get_company", "get_profile (partial)"],
            "with_login": ["search_people", "get_profile (full)"],
        },
    })


@api_bp.route("/login", methods=["POST"])
def api_login():
    """Trigger the LinkedIn login flow (opens a headed browser on server)."""
    success = run_async_with_retry("login")

    if success:
        return jsonify({
            "status": "success",
            "message": "LinkedIn session saved. All features are now available.",
        })
    else:
        return jsonify({
            "status": "failed",
            "message": "Login was not completed. Please try again.",
        }), 400


@api_bp.route("/profile", methods=["POST"])
def api_get_profile():
    """Fetch a LinkedIn profile by URL or username."""
    data = request.get_json(silent=True) or {}
    profile_url = (data.get("profile_url") or "").strip()
    username = (data.get("username") or "").strip()

    if not profile_url and not username:
        return jsonify({"error": "Provide either profile_url or username"}), 400

    profile = run_async_with_retry("get_profile", profile_url=profile_url, username=username)

    if not profile:
        has_session = (SESSION_DIR / "linkedin.json").exists()
        msg = "Could not fetch profile."
        if not has_session:
            msg += " Try logging in first for full access."
        return jsonify({"error": msg}), 404

    return jsonify(profile.to_dict())


@api_bp.route("/search/people", methods=["POST"])
def api_search_people():
    """Search for people on LinkedIn (requires login)."""
    has_session = (SESSION_DIR / "linkedin.json").exists()
    if not has_session:
        return jsonify({"error": "Login required for people search."}), 401

    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({"error": "Search query is required"}), 400

    result = run_async_with_retry(
        "search_people",
        query=query,
        location=(data.get("location") or ""),
        company=(data.get("company") or ""),
        title=(data.get("title") or ""),
        max_results=min(int(data.get("max_results") or 20), 50)
    )

    return jsonify(result.to_dict())


@api_bp.route("/search/jobs", methods=["POST"])
def api_search_jobs():
    """Search for jobs on LinkedIn (no login required)."""
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({"error": "Search query is required"}), 400

    result = run_async_with_retry(
        "search_jobs",
        query=query,
        location=(data.get("location") or ""),
        remote=(data.get("remote") or ""),
        job_type=(data.get("job_type") or ""),
        experience=(data.get("experience") or ""),
        max_results=min(int(data.get("max_results") or 25), 50)
    )

    return jsonify(result.to_dict())


@api_bp.route("/company", methods=["POST"])
def api_get_company():
    """Fetch LinkedIn company page data."""
    data = request.get_json(silent=True) or {}
    company_url = (data.get("company_url") or "").strip()
    company_slug = (data.get("company_slug") or "").strip()

    if not company_url and not company_slug:
        return jsonify({"error": "Provide either company_url or company_slug"}), 400

    company = run_async_with_retry("get_company", company_url=company_url, company_slug=company_slug)

    if not company:
        return jsonify({"error": "Could not fetch company data"}), 404

    return jsonify(company.to_dict())


@api_bp.route("/export", methods=["POST"])
def api_export():
    """Export results as CSV or JSON file download."""
    data = request.get_json(silent=True) or {}
    fmt = (data.get("format") or "json").lower()
    results = data.get("results") or []
    filename = (data.get("filename") or "linkedin_export")

    if not results:
        return jsonify({"error": "No data to export"}), 400

    if fmt == "csv":
        if not isinstance(results, list):
            results = [results]

        all_keys = []
        for row in results:
            if isinstance(row, dict):
                for k in row.keys():
                    if k not in all_keys:
                        all_keys.append(k)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        for row in results:
            if isinstance(row, dict):
                csv_row = {}
                for k, v in row.items():
                    if isinstance(v, list):
                        csv_row[k] = ", ".join(str(i) for i in v)
                    else:
                        csv_row[k] = v
                writer.writerow(csv_row)

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )
    else:
        return Response(
            json.dumps(results, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}.json"},
        )
