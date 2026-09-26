import os
import json
import time
from flask import Flask, render_template, request, jsonify, session
from config import BASE_DIR, STATIC_DIR, PORT, HOST, DEBUG, SECRET_KEY, ALLOWED_TARGET_DOMAINS, ALLOW_EXTERNAL_TARGET_URLS
from database import get_db_connection, init_db
from auth import register_user, authenticate_user, login_required, get_current_user
from url_validator import is_safe_target_url
from engine.ai_generator import ai_engine
from engine.execution_queue import execution_queue
from engine.java_generator import java_generator
from engine.test_data_factory import test_data_factory

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = SECRET_KEY

# Initialize database schema on startup
init_db()

# ----------------- WEB PAGES -----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/app/target-store")
def target_store():
    return render_template("target_app.html")

# ----------------- AUTHENTICATION REST APIS -----------------

@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.json or {}
    username = data.get("username", "")
    email = data.get("email", "")
    password = data.get("password", "")
    full_name = data.get("full_name", "QA Engineer")
    role = data.get("role", "Tester")

    success, msg, user_data = register_user(username, email, password, full_name, role)
    if not success:
        return jsonify({"success": False, "error": msg}), 400

    session["user"] = user_data
    return jsonify({"success": True, "message": msg, "user": user_data})

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.json or {}
    identifier = data.get("username") or data.get("email", "")
    password = data.get("password", "")

    success, msg, user_data = authenticate_user(identifier, password)
    if not success:
        return jsonify({"success": False, "error": msg}), 401

    session["user"] = user_data
    return jsonify({"success": True, "message": msg, "user": user_data})

@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.pop("user", None)
    return jsonify({"success": True, "message": "Logged out successfully."})

@app.route("/api/auth/me", methods=["GET"])
def api_current_user():
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False, "user": None})
    return jsonify({"authenticated": True, "user": user})

# ----------------- DASHBOARD & METRICS APIS -----------------

@app.route("/api/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total Test Cases & 4-State Breakdown
    cursor.execute("SELECT COUNT(*) FROM test_cases")
    total_tc = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM test_cases WHERE status = 'APPROVED'")
    approved_tc = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM test_cases WHERE status = 'IN_REVIEW'")
    in_review_tc = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM test_cases WHERE status = 'DRAFT'")
    draft_tc = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM test_cases WHERE status = 'REJECTED'")
    rejected_tc = cursor.fetchone()[0]

    # Active Bugs
    cursor.execute("SELECT COUNT(*) FROM bug_reports WHERE status = 'OPEN'")
    active_bugs = cursor.fetchone()[0]

    # Recent Test Runs
    cursor.execute("SELECT * FROM test_runs ORDER BY id DESC LIMIT 15")
    runs = [dict(row) for row in cursor.fetchall()]

    # Real Measured Success Rate (Historical Lifetime)
    cursor.execute("SELECT COUNT(*), SUM(passed_tests), SUM(total_tests) FROM test_runs WHERE status = 'COMPLETED'")
    sum_row = cursor.fetchone()
    completed_runs_count = sum_row[0] or 0
    total_passed = sum_row[1] or 0
    total_executed = sum_row[2] or 0
    success_rate = round((total_passed / total_executed * 100), 1) if total_executed > 0 else 0.0

    # Calculate Requirement Coverage Breakdown
    cursor.execute("SELECT * FROM requirements ORDER BY id ASC")
    raw_reqs = [dict(row) for row in cursor.fetchall()]
    total_reqs = len(raw_reqs)

    req_coverage_list = []
    covered_reqs = 0
    partially_covered_reqs = 0
    uncovered_reqs = 0

    for r in raw_reqs:
        cursor.execute("""
            SELECT 
                COUNT(*) as total_tc,
                SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved_tc,
                SUM(CASE WHEN status = 'IN_REVIEW' THEN 1 ELSE 0 END) as in_review_tc,
                SUM(CASE WHEN status = 'DRAFT' THEN 1 ELSE 0 END) as draft_tc
            FROM test_cases WHERE req_id = ?
        """, (r["id"],))
        c_row = dict(cursor.fetchone())
        r_total = c_row["total_tc"] or 0
        r_approved = c_row["approved_tc"] or 0
        r_in_review = c_row["in_review_tc"] or 0
        r_draft = c_row["draft_tc"] or 0

        if r_total == 0:
            status_cov = "UNCOVERED"
            uncovered_reqs += 1
        elif r_approved > 0 and r_approved >= r_total:
            status_cov = "COVERED"
            covered_reqs += 1
        else:
            status_cov = "PARTIALLY_COVERED"
            partially_covered_reqs += 1

        req_coverage_list.append({
            "id": r["id"],
            "title": r["title"],
            "module_name": r["module_name"],
            "version": r.get("version", 1),
            "total_test_cases": r_total,
            "approved_test_cases": r_approved,
            "in_review_test_cases": r_in_review,
            "draft_test_cases": r_draft,
            "coverage_status": status_cov
        })

    req_coverage_pct = round((covered_reqs / total_reqs * 100), 1) if total_reqs > 0 else 0.0

    # Regression summary between latest two completed runs
    cursor.execute("SELECT * FROM test_runs WHERE status = 'COMPLETED' ORDER BY id DESC LIMIT 2")
    last_two_runs = [dict(row) for row in cursor.fetchall()]
    regression_info = {
        "status": "NO_RUNS",
        "badge_text": "No History",
        "message": "No completed runs recorded yet."
    }
    if len(last_two_runs) == 1:
        latest = last_two_runs[0]
        exec_mode = latest.get("execution_mode", "Selenium")
        if latest["failed_tests"] == 0:
            regression_info = {
                "status": "CLEAN",
                "badge_text": f"Clean Run ({exec_mode})",
                "message": f"Run #{latest['id']} ({exec_mode} • {latest['suite_name']}): 100% tests passing ({latest['passed_tests']}/{latest['total_tests']}) with 0 regressions."
            }
        else:
            regression_info = {
                "status": "DEFECTS",
                "badge_text": f"{latest['failed_tests']} Failures ({exec_mode})",
                "message": f"Run #{latest['id']} ({exec_mode}) has {latest['failed_tests']} failure(s) requiring triage."
            }
    elif len(last_two_runs) >= 2:
        latest = last_two_runs[0]
        prev = last_two_runs[1]
        lat_mode = latest.get("execution_mode", "Selenium")
        prev_mode = prev.get("execution_mode", "Selenium")

        if latest["failed_tests"] == 0 and prev["failed_tests"] == 0:
            regression_info = {
                "status": "CLEAN",
                "badge_text": f"Clean Run ({lat_mode})",
                "message": f"Latest Run #{latest['id']} ({lat_mode}) matches previous Run #{prev['id']} ({prev_mode}) with zero regressions."
            }
        elif latest["failed_tests"] > 0 and prev["failed_tests"] == 0:
            regression_info = {
                "status": "REGRESSION_DETECTED",
                "badge_text": f"Regression ({lat_mode})",
                "message": f"⚠️ Regression Alert: Run #{latest['id']} ({lat_mode}) has {latest['failed_tests']} new failure(s) compared to clean Run #{prev['id']} ({prev_mode})."
            }
        elif latest["failed_tests"] == 0 and prev["failed_tests"] > 0:
            regression_info = {
                "status": "REGRESSION_RESOLVED",
                "badge_text": f"Fixed ({lat_mode})",
                "message": f"🎉 Fixed: Run #{latest['id']} ({lat_mode}) resolved {prev['failed_tests']} failure(s) from Run #{prev['id']} ({prev_mode})."
            }
        else:
            regression_info = {
                "status": "FAILURES_PERSISTING",
                "badge_text": f"Failures ({lat_mode})",
                "message": f"Ongoing failures: Run #{latest['id']} ({lat_mode}) has {latest['failed_tests']} failures (vs {prev['failed_tests']} in Run #{prev['id']} [{prev_mode}])."
            }

    # Fetch all test cases with requirement title & reviewer
    cursor.execute("""
        SELECT tc.*, r.title as requirement_title, r.module_name
        FROM test_cases tc
        LEFT JOIN requirements r ON tc.req_id = r.id
        ORDER BY tc.id DESC
    """)
    all_test_cases = [dict(row) for row in cursor.fetchall()]

    # Fetch bug reports
    cursor.execute("SELECT * FROM bug_reports ORDER BY id DESC")
    all_bugs = [dict(row) for row in cursor.fetchall()]

    ai_status = ai_engine.get_engine_status()

    # Dynamic Workflow Guidance calculation
    if total_reqs == 0:
        active_step = "ingest"
        stage_title = "Step 1: Ingest Requirements"
        guidance_desc = "Add functional user stories to automatically generate BDD scenarios."
        action_label = "Create Requirement"
        action_target = "requirements-view"
    elif total_tc == 0:
        active_step = "generate"
        stage_title = "Step 2: Generate Test Cases"
        guidance_desc = "Use AI Copilot to generate comprehensive BDD test cases."
        action_label = "Generate Scenarios"
        action_target = "requirements-view"
    elif (draft_tc + in_review_tc) > 0:
        active_step = "approve"
        stage_title = "Step 3: Review & Approve Scenarios"
        if in_review_tc > 0 and draft_tc > 0:
            guidance_desc = f"{in_review_tc} scenario(s) in review queue, {draft_tc} draft scenario(s) awaiting submission for review."
        elif in_review_tc > 0:
            guidance_desc = f"{in_review_tc} scenario(s) submitted for QA peer review and awaiting sign-off."
        else:
            guidance_desc = f"{draft_tc} draft scenario(s) are awaiting submission for review."
        action_label = "Review Scenarios"
        action_target = "testcases-view"
    elif active_bugs > 0:
        active_step = "triage"
        stage_title = "Step 5: Triage Defects & AI RCA"
        guidance_desc = f"{active_bugs} unresolved defect(s) detected. Review AI root cause analysis and recommendations."
        action_label = "Triage Bugs"
        action_target = "bugs-view"
    else:
        active_step = "exec"
        stage_title = "Step 4: Execute Automation Suite"
        guidance_desc = f"{approved_tc} approved test case(s) ready for execution via Selenium or In-Memory engine."
        action_label = "Execute Suite"
        action_target = "runner-view"

    workflow_guidance = {
        "active_step": active_step,
        "stage_title": stage_title,
        "description": guidance_desc,
        "action_label": action_label,
        "action_target": action_target
    }

    metric_explanations = {
        "success_rate": {
            "title": "Test Success Rate",
            "formula": f"{total_passed} Passed / {total_executed} Total Tests Executed ({success_rate}%)",
            "period": f"All {completed_runs_count} recorded automation runs in DB",
            "source": "Aggregated execution logs from test_runs & test_results",
            "notes": "Reflects overall health across all executed regression test suites."
        },
        "code_coverage": {
            "title": "Requirement Coverage (Scope)",
            "formula": f"{covered_reqs} Covered / {total_reqs} User Stories ({req_coverage_pct}%)",
            "period": "Active Repository Scope",
            "source": "Requirements mapped to Approved Test Cases",
            "notes": "Indicates user story coverage; not JaCoCo line/branch bytecode coverage."
        },
        "requirement_coverage": {
            "title": "Requirement Coverage (Scope)",
            "formula": f"{covered_reqs} Covered / {total_reqs} User Stories ({req_coverage_pct}%)",
            "period": "Active Repository Scope",
            "source": "Requirements mapped to Approved Test Cases",
            "notes": "Indicates user story coverage; not JaCoCo line/branch bytecode coverage."
        },
        "total_test_cases": {
            "title": "Total Test Cases",
            "formula": f"{approved_tc} Approved + {in_review_tc} In Review + {draft_tc} Draft + {rejected_tc} Rejected = {total_tc}",
            "period": "Current database state",
            "source": "test_cases table",
            "notes": "Only Approved test cases are queued into test execution suites."
        },
        "active_bugs": {
            "title": "Active Bugs Detected",
            "formula": f"{active_bugs} unresolved issues with status 'OPEN'",
            "period": "Open defects across all test runs",
            "source": "Automated assertion failures & AI RCA bug reports",
            "notes": "Includes defect severity and AI root cause analysis."
        }
    }

    coverage_counts = {
        "covered": covered_reqs,
        "partially_covered": partially_covered_reqs,
        "uncovered": uncovered_reqs,
        "total": total_reqs
    }

    return jsonify({
        "success_rate": success_rate,
        "total_passed": total_passed,
        "total_executed": total_executed,
        "total_passed_tests": total_passed,
        "total_executed_tests": total_executed,
        "completed_runs_count": completed_runs_count,
        "success_rate_formula": f"{total_passed} Passed / {total_executed} Total Tests Executed",
        "success_rate_period": f"All {completed_runs_count} recorded automation runs in DB",
        
        "code_coverage": req_coverage_pct,
        "requirement_coverage": req_coverage_pct,
        "total_requirements": total_reqs,
        "covered_requirements": covered_reqs,
        "partially_covered_requirements": partially_covered_reqs,
        "uncovered_requirements": uncovered_reqs,
        "coverage_formula": f"{covered_reqs} Covered / {total_reqs} User Stories (Functional Scope)",
        "coverage_source": "Approved Test Cases mapped to Requirements (Not Bytecode / JaCoCo)",
        "coverage_counts": coverage_counts,
        "requirement_coverage_list": req_coverage_list,
        "requirements_coverage_list": req_coverage_list,

        "total_test_cases": total_tc,
        "approved_test_cases": approved_tc,
        "in_review_test_cases": in_review_tc,
        "draft_test_cases": draft_tc,
        "rejected_test_cases": rejected_tc,
        "test_cases_source": "Current SQLite Repository Snapshot",

        "active_bugs": active_bugs,
        "active_bugs_source": "Automated Assertions & AI RCA",
        "active_bugs_period": "Active / Unresolved in current repository",

        "recent_runs": runs,
        "regression_info": regression_info,
        "workflow_guidance": workflow_guidance,
        "metric_explanations": metric_explanations,
        "ai_status": ai_status,
        "test_cases": all_test_cases,
        "bug_reports": all_bugs
    })

@app.route("/api/ai/status", methods=["GET"])
def get_ai_copilot_status():
    """Returns AI Copilot connection, provider, mode, trust level and latency."""
    return jsonify(ai_engine.get_engine_status())

# ----------------- REQUIREMENTS & IMPACT ANALYSIS -----------------

@app.route("/api/requirements", methods=["GET"])
def get_requirements():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM requirements ORDER BY id DESC")
    reqs = [dict(row) for row in cursor.fetchall()]

    # Attach test case counts & coverage per requirement
    for r in reqs:
        cursor.execute("SELECT COUNT(*), SUM(CASE WHEN status='APPROVED' THEN 1 ELSE 0 END) FROM test_cases WHERE req_id = ?", (r["id"],))
        tc_counts = cursor.fetchone()
        r["total_test_cases"] = tc_counts[0] or 0
        r["approved_test_cases"] = tc_counts[1] or 0
        r["is_covered"] = (r["approved_test_cases"] > 0)

    conn.close()
    return jsonify({"requirements": reqs})

@app.route("/api/requirements/<int:req_id>", methods=["PUT"])
def update_requirement(req_id):
    """Updates requirement and triggers Impact Analysis (flags linked test cases as needs_review)."""
    data = request.json or {}
    title = data.get("title")
    description = data.get("description")
    module_name = data.get("module_name")
    acceptance_criteria = data.get("acceptance_criteria")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Update requirement & increment version
    cursor.execute("""
    UPDATE requirements
    SET title = ?, description = ?, module_name = ?, acceptance_criteria = ?,
        version = version + 1, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (title, description, module_name, acceptance_criteria, req_id))

    # Impact Analysis: Flag all linked test cases as needs_review = 1 and update APPROVED to IN_REVIEW
    cursor.execute("""
    UPDATE test_cases 
    SET needs_review = 1,
        status = CASE WHEN status = 'APPROVED' THEN 'IN_REVIEW' ELSE status END
    WHERE req_id = ?
    """, (req_id,))
    impacted_count = cursor.rowcount

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "id": req_id,
        "impact_analysis": {
            "impacted_test_cases_count": impacted_count,
            "message": f"Requirement updated to new version. {impacted_count} linked test case(s) flagged as 'NEEDS_REVIEW'."
        }
    })

@app.route("/api/traceability/matrix", methods=["GET"])
def get_traceability_matrix():
    """Returns end-to-end relational mapping: Requirement -> Test Cases -> Test Results -> Defects."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM requirements ORDER BY id ASC")
    reqs = [dict(row) for row in cursor.fetchall()]

    matrix = []
    for r in reqs:
        cursor.execute("SELECT * FROM test_cases WHERE req_id = ?", (r["id"],))
        tcs = [dict(row) for row in cursor.fetchall()]

        for tc in tcs:
            cursor.execute("SELECT * FROM test_results WHERE test_case_id = ? ORDER BY id DESC LIMIT 1", (tc["id"],))
            latest_res = cursor.fetchone()
            tc["latest_result"] = dict(latest_res) if latest_res else None

            cursor.execute("SELECT * FROM bug_reports WHERE test_case_id = ? OR test_result_id = ?", (tc["id"], tc["latest_result"]["id"] if tc["latest_result"] else -1))
            bugs = [dict(row) for row in cursor.fetchall()]
            tc["bugs"] = bugs

        matrix.append({
            "requirement": r,
            "test_cases": tcs
        })

    conn.close()
    return jsonify({"matrix": matrix})

# ----------------- AI TEST GENERATION -----------------

@app.route("/api/generate-testcases", methods=["POST"])
def generate_testcases():
    data = request.json or {}
    title = data.get("title", "Feature Verification")
    module_name = data.get("module_name", "General")
    description = data.get("description", "")
    acceptance_criteria = data.get("acceptance_criteria", "")
    test_types = data.get("test_types", ["Functional", "Negative", "Boundary", "Security"])

    conn = get_db_connection()
    cursor = conn.cursor()

    # Save requirement
    cursor.execute("""
    INSERT INTO requirements (title, description, module_name, acceptance_criteria, version, status)
    VALUES (?, ?, ?, ?, 1, 'ACTIVE')
    """, (title, description, module_name, acceptance_criteria))
    req_id = cursor.lastrowid

    # Generate test cases using AI engine
    generated_cases, provider = ai_engine.generate_test_cases(
        title=title,
        description=description,
        module_name=module_name,
        acceptance_criteria=acceptance_criteria,
        test_types=test_types
    )

    saved_cases = []
    for tc in generated_cases:
        steps_str = json.dumps(tc.get("steps_json", [])) if isinstance(tc.get("steps_json"), (list, dict)) else str(tc.get("steps_json", "[]"))
        cursor.execute("""
        INSERT INTO test_cases (req_id, title, test_type, priority, gherkin_text, pre_conditions, steps_json, expected_result, status, provider)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req_id,
            tc.get("title"),
            tc.get("test_type", "Functional"),
            tc.get("priority", "Medium"),
            tc.get("gherkin_text"),
            tc.get("pre_conditions"),
            steps_str,
            tc.get("expected_result"),
            "DRAFT",
            provider
        ))
        tc_id = cursor.lastrowid
        tc_dict = dict(tc)
        tc_dict["id"] = tc_id
        tc_dict["req_id"] = req_id
        tc_dict["status"] = "DRAFT"
        tc_dict["provider"] = provider
        saved_cases.append(tc_dict)

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "requirement_id": req_id,
        "provider": provider,
        "test_cases": saved_cases
    })

@app.route("/api/testcases/<int:tc_id>/status", methods=["PATCH"])
def update_testcase_status(tc_id):
    data = request.json or {}
    new_status = data.get("status", "APPROVED").upper()
    if new_status not in ("DRAFT", "IN_REVIEW", "APPROVED", "REJECTED"):
        new_status = "APPROVED"

    user = get_current_user()
    reviewer = data.get("reviewer") or (user["full_name"] if user else "Lead QA Architect")
    review_notes = data.get("review_notes", "")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE test_cases 
        SET status = ?, 
            reviewer = ?, 
            review_notes = ?, 
            reviewed_at = CURRENT_TIMESTAMP, 
            needs_review = 0, 
            updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (new_status, reviewer, review_notes, tc_id))
    conn.commit()

    cursor.execute("""
        SELECT tc.*, r.title as requirement_title, r.module_name
        FROM test_cases tc 
        LEFT JOIN requirements r ON tc.req_id = r.id 
        WHERE tc.id = ?
    """, (tc_id,))
    updated_row = cursor.fetchone()
    conn.close()

    if not updated_row:
        return jsonify({"error": "Test case not found"}), 404

    return jsonify({"success": True, "id": tc_id, "status": new_status, "reviewer": reviewer, "test_case": dict(updated_row)})

@app.route("/api/testcases/<int:tc_id>", methods=["GET"])
def get_testcase_details(tc_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tc.*, r.title as requirement_title, r.module_name
        FROM test_cases tc
        LEFT JOIN requirements r ON tc.req_id = r.id
        WHERE tc.id = ?
    """, (tc_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(row))

# ----------------- ASYNCHRONOUS TEST RUNNER & SSRF VALIDATION -----------------

@app.route("/api/execute-test", methods=["POST"])
def execute_tests():
    data = request.json or {}
    suite = data.get("suite", "all")
    target_url = data.get("target_url", "http://127.0.0.1:5000/app/target-store")
    exec_mode = data.get("exec_mode", "Selenium")

    # SSRF & Target URL Security Validation
    is_safe, error_msg = is_safe_target_url(
        target_url,
        allowed_domains=ALLOWED_TARGET_DOMAINS,
        allow_external=ALLOW_EXTERNAL_TARGET_URLS
    )
    if not is_safe:
        return jsonify({
            "success": False,
            "error": "Target URL Security Validation Failed",
            "message": error_msg
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Query approved test cases
    if suite == "auth":
        cursor.execute("SELECT * FROM test_cases WHERE status = 'APPROVED' AND (title LIKE '%login%' OR test_type = 'Security')")
    elif suite == "search":
        cursor.execute("SELECT * FROM test_cases WHERE status = 'APPROVED' AND (title LIKE '%search%' OR title LIKE '%catalog%')")
    elif suite == "checkout":
        cursor.execute("SELECT * FROM test_cases WHERE status = 'APPROVED' AND (title LIKE '%cart%' OR title LIKE '%checkout%')")
    else:
        cursor.execute("SELECT * FROM test_cases WHERE status = 'APPROVED'")

    approved_cases = [dict(row) for row in cursor.fetchall()]
    if not approved_cases:
        cursor.execute("SELECT * FROM test_cases LIMIT 5")
        approved_cases = [dict(row) for row in cursor.fetchall()]

    suite_title = f"Regression Suite ({suite.capitalize()})"

    # Terminology standardization
    if exec_mode.lower() in ("selenium", "real", "webdriver", "real selenium", "real selenium webdriver"):
        std_exec_mode = "Real Selenium WebDriver"
        is_simulated = 0
        browser_info = "Chrome Headless (v124)"
        env_info = "Windows 64-bit / Localhost"
    else:
        std_exec_mode = "Simulated (In-Memory Engine)"
        is_simulated = 1
        browser_info = "Built-in DOM Simulator"
        env_info = "In-Memory Python Fast Engine"

    # Insert initial run in QUEUED state
    cursor.execute("""
    INSERT INTO test_runs (suite_name, total_tests, passed_tests, failed_tests, execution_mode, is_simulated, browser, environment, status)
    VALUES (?, ?, 0, 0, ?, ?, ?, ?, 'QUEUED')
    """, (suite_title, len(approved_cases), std_exec_mode, is_simulated, browser_info, env_info))
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Submit job to background thread execution queue
    execution_queue.submit_test_run(
        run_id=run_id,
        suite_name=suite_title,
        test_cases=approved_cases,
        target_url=target_url,
        exec_mode=exec_mode
    )

    return jsonify({
        "success": True,
        "run_id": run_id,
        "status": "QUEUED",
        "total_tests": len(approved_cases),
        "execution_mode": std_exec_mode,
        "browser": browser_info,
        "environment": env_info,
        "message": f"Test run #{run_id} successfully queued into asynchronous background executor."
    })

@app.route("/api/test-runs/compare", methods=["GET"])
def compare_test_runs():
    """Compares two execution runs side-by-side with pass rate delta, duration delta, and test diffs."""
    run_a_id = request.args.get("run_a", type=int)
    run_b_id = request.args.get("run_b", type=int)

    if not run_a_id or not run_b_id:
        return jsonify({"error": "Both run_a and run_b parameters are required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM test_runs WHERE id = ?", (run_a_id,))
    row_a = cursor.fetchone()
    cursor.execute("SELECT * FROM test_runs WHERE id = ?", (run_b_id,))
    row_b = cursor.fetchone()

    if not row_a or not row_b:
        conn.close()
        return jsonify({"error": "One or both runs could not be found"}), 404

    run_a = dict(row_a)
    run_b = dict(row_b)

    cursor.execute("SELECT * FROM test_results WHERE run_id = ? ORDER BY id ASC", (run_a_id,))
    results_a = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM test_results WHERE run_id = ? ORDER BY id ASC", (run_b_id,))
    results_b = [dict(r) for r in cursor.fetchall()]

    conn.close()

    map_a = {r["test_title"]: r for r in results_a}
    map_b = {r["test_title"]: r for r in results_b}
    all_titles = list(dict.fromkeys(list(map_a.keys()) + list(map_b.keys())))

    diff_list = []
    regressions_count = 0
    fixes_count = 0

    for title in all_titles:
        res_a = map_a.get(title)
        res_b = map_b.get(title)

        status_a = res_a["status"] if res_a else "NOT_IN_RUN"
        status_b = res_b["status"] if res_b else "NOT_IN_RUN"

        if status_a == "PASSED" and status_b == "FAILED":
            diff_type = "REGRESSION"
            regressions_count += 1
        elif status_a == "FAILED" and status_b == "PASSED":
            diff_type = "FIXED"
            fixes_count += 1
        elif status_a == status_b:
            diff_type = "UNCHANGED"
        else:
            diff_type = "CHANGED"

        diff_list.append({
            "test_title": title,
            "status_a": status_a,
            "status_b": status_b,
            "duration_a": res_a.get("execution_time_sec", 0.0) if res_a else 0.0,
            "duration_b": res_b.get("execution_time_sec", 0.0) if res_b else 0.0,
            "error_a": res_a.get("error_message") if res_a else None,
            "error_b": res_b.get("error_message") if res_b else None,
            "diff_type": diff_type
        })

    duration_delta = round((run_b.get("duration_sec", 0.0) or 0.0) - (run_a.get("duration_sec", 0.0) or 0.0), 2)
    pass_rate_a = round((run_a["passed_tests"] / run_a["total_tests"] * 100), 1) if run_a.get("total_tests") else 0.0
    pass_rate_b = round((run_b["passed_tests"] / run_b["total_tests"] * 100), 1) if run_b.get("total_tests") else 0.0
    pass_rate_delta = round(pass_rate_b - pass_rate_a, 1)

    return jsonify({
        "success": True,
        "run_a": run_a,
        "run_b": run_b,
        "pass_rate_a": pass_rate_a,
        "pass_rate_b": pass_rate_b,
        "pass_rate_delta": pass_rate_delta,
        "duration_delta": duration_delta,
        "regressions_count": regressions_count,
        "fixes_count": fixes_count,
        "deltas": {
            "pass_rate_diff": pass_rate_delta,
            "duration_diff_sec": duration_delta,
            "regressions_count": regressions_count,
            "fixes_count": fixes_count
        },
        "test_diffs": diff_list
    })

@app.route("/api/defects/details", methods=["GET"])
def get_defect_details():
    """Returns active defects or failures for a specific run with error message and screenshots."""
    run_id = request.args.get("run_id", type=int)
    conn = get_db_connection()
    cursor = conn.cursor()

    if run_id:
        cursor.execute("""
            SELECT tr.*, tc.title as test_case_title, tc.test_type, tc.priority, r.title as req_title,
                   br.id as bug_id, br.severity, br.root_cause_analysis, br.summary as bug_summary, br.steps_to_reproduce
            FROM test_results tr
            LEFT JOIN test_cases tc ON tr.test_case_id = tc.id
            LEFT JOIN requirements r ON tr.req_id = r.id
            LEFT JOIN bug_reports br ON br.test_result_id = tr.id
            WHERE tr.run_id = ? AND tr.status = 'FAILED'
            ORDER BY tr.id ASC
        """, (run_id,))
    else:
        cursor.execute("""
            SELECT br.id as bug_id, br.title as bug_title, br.severity, br.module, br.summary as bug_summary,
                   br.steps_to_reproduce, br.actual_result, br.expected_result, br.root_cause_analysis,
                   br.ai_fix_suggestion, br.status as bug_status, br.created_at,
                   tr.id as test_result_id, tr.test_title, tr.error_message, tr.stack_trace, tr.screenshot_path,
                   tc.id as test_case_id, r.title as req_title
            FROM bug_reports br
            LEFT JOIN test_results tr ON br.test_result_id = tr.id
            LEFT JOIN test_cases tc ON br.test_case_id = tc.id
            LEFT JOIN requirements r ON br.req_id = r.id
            WHERE br.status = 'OPEN'
            ORDER BY br.id DESC
        """)

    defects = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify({"success": True, "defects": defects, "run_id": run_id, "count": len(defects)})

@app.route("/api/test-runs/<int:run_id>/status", methods=["GET"])
def get_test_run_status(run_id):
    """Polling endpoint for real-time progress of asynchronous test runs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM test_runs WHERE id = ?", (run_id,))
    run_row = cursor.fetchone()

    if not run_row:
        conn.close()
        return jsonify({"error": "Run not found"}), 404

    run_dict = dict(run_row)
    active_progress = execution_queue.get_job_progress(run_id)

    # Fetch test results if completed or partial
    cursor.execute("SELECT * FROM test_results WHERE run_id = ? ORDER BY id ASC", (run_id,))
    results = [dict(r) for r in cursor.fetchall()]
    conn.close()

    run_dict["results"] = results
    run_dict["in_memory_progress"] = active_progress

    return jsonify(run_dict)

@app.route("/api/test-runs/<int:run_id>/cancel", methods=["POST"])
def cancel_test_run(run_id):
    cancelled = execution_queue.request_cancellation(run_id)
    return jsonify({"success": cancelled, "run_id": run_id})

# ----------------- AI BUG REPORTS & RCA -----------------

@app.route("/api/generate-bug-report", methods=["POST"])
def generate_bug_report_endpoint():
    data = request.json or {}
    test_result_id = data.get("test_result_id")
    test_case_id = data.get("test_case_id")
    req_id = data.get("req_id")
    test_title = data.get("test_title", "Unknown Test Failure")
    error_message = data.get("error_message", "")
    stack_trace = data.get("stack_trace", "")
    browser_logs = data.get("browser_logs", "")

    analysis = ai_engine.analyze_failure_and_generate_bug_report(
        test_title=test_title,
        error_message=error_message,
        stack_trace=stack_trace,
        browser_logs=browser_logs
    )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO bug_reports (test_result_id, req_id, test_case_id, title, severity, module, summary, steps_to_reproduce, actual_result, expected_result, root_cause_analysis, ai_fix_suggestion, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        test_result_id,
        req_id,
        test_case_id,
        analysis["title"],
        analysis["severity"],
        analysis["module"],
        analysis["summary"],
        analysis["steps_to_reproduce"],
        analysis["actual_result"],
        analysis["expected_result"],
        analysis["root_cause_analysis"],
        analysis["ai_fix_suggestion"],
        "OPEN"
    ))
    bug_id = cursor.lastrowid
    conn.commit()
    conn.close()

    analysis["id"] = bug_id
    return jsonify({"success": True, "bug_report": analysis})

# ----------------- MISC APIS -----------------

@app.route("/api/test-data", methods=["GET"])
def get_test_data():
    return jsonify({
        "emails": test_data_factory.get_email_datasets(),
        "passwords": test_data_factory.get_password_datasets(),
        "boundary_numbers": test_data_factory.get_boundary_numbers(),
        "security_vectors": test_data_factory.get_security_vectors(),
        "synthetic_profiles": test_data_factory.generate_synthetic_profiles(5)
    })

@app.route("/api/export/code", methods=["GET"])
def export_code():
    code_type = request.args.get("type", "java-test")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM test_cases WHERE status = 'APPROVED'")
    approved_cases = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if code_type == "java-test":
        code = java_generator.generate_testng_class("EcommerceRegressionSuite", approved_cases)
        return jsonify({"filename": "EcommerceRegressionTest.java", "code": code})
    elif code_type == "java-pom":
        code = java_generator.generate_pom_login_class()
        return jsonify({"filename": "LoginPage.java", "code": code})
    elif code_type == "maven-pom":
        code = java_generator.generate_maven_pom()
        return jsonify({"filename": "pom.xml", "code": code})
    elif code_type == "python-pytest":
        code = java_generator.generate_python_pytest(approved_cases)
        return jsonify({"filename": "test_suite.py", "code": code})

    return jsonify({"filename": "Unknown", "code": "// Invalid type requested"})

@app.route("/api/ai-chat", methods=["POST"])
def ai_chat_endpoint():
    data = request.json or {}
    message = data.get("message", "")
    response = ai_engine.chat_with_copilot(message)
    return jsonify(response)

@app.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.json or {}
    conn = get_db_connection()
    cursor = conn.cursor()
    for k, v in data.items():
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == "__main__":
    print(f"[START] AI-Powered QA Testing Assistant running on http://{HOST}:{PORT} (DEBUG={DEBUG})")
    app.run(host=HOST, port=PORT, debug=DEBUG)
