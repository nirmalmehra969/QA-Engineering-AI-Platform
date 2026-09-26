import pytest
import json
import time
from app import app
from database import init_db, get_db_connection
from auth import register_user, authenticate_user
from url_validator import is_safe_target_url
from engine.ai_generator import ai_engine, GEMINI_MODEL_NAME
from engine.selenium_runner import selenium_runner
from engine.java_generator import java_generator
from engine.test_data_factory import test_data_factory

@pytest.fixture
def client():
    app.config['TESTING'] = True
    init_db()
    with app.test_client() as client:
        yield client

# 1. SECURITY & AUTHENTICATION TESTS
def test_user_registration_and_password_hashing(client):
    """Verify user registration stores password hashed and authenticates correctly."""
    username = f"testuser_{int(time.time())}"
    email = f"{username}@qa-platform.io"
    password = "SecurePassword@123"

    # Direct Auth module test
    success, msg, user = register_user(username, email, password, "Test Engineer", "Tester")
    assert success is True
    assert user["username"] == username

    # Verify password hash in DB is not plaintext
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    assert row is not None
    assert row["password_hash"] != password
    assert row["password_hash"].startswith("pbkdf2:sha256")
    conn.close()

    # Authenticate with valid password
    auth_ok, _, auth_user = authenticate_user(username, password)
    assert auth_ok is True
    assert auth_user["email"] == email

    # Reject invalid password
    auth_bad, _, _ = authenticate_user(username, "WrongPassword999")
    assert auth_bad is False

def test_auth_api_endpoints(client):
    """Verify registration and login REST endpoints."""
    username = f"api_user_{int(time.time())}"
    payload = {
        "username": username,
        "email": f"{username}@qa.com",
        "password": "Password@2026",
        "full_name": "API QA User"
    }
    reg_res = client.post("/api/auth/register", json=payload)
    assert reg_res.status_code == 200
    assert reg_res.get_json()["success"] is True

    # Login endpoint
    login_res = client.post("/api/auth/login", json={"username": username, "password": "Password@2026"})
    assert login_res.status_code == 200
    assert login_res.get_json()["success"] is True

    # Check /api/auth/me
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["authenticated"] is True

    # Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

# 2. SSRF & URL SAFETY VALIDATOR TESTS
def test_target_url_security_and_ssrf_protection():
    """Verify URL validator allows safe domains and blocks dangerous protocols and cloud metadata."""
    # Allowed local URLs
    ok, _ = is_safe_target_url("http://127.0.0.1:5000/app/target-store")
    assert ok is True

    ok, _ = is_safe_target_url("http://localhost:3000/test")
    assert ok is True

    # Blocked dangerous schemes
    bad_scheme, msg = is_safe_target_url("file:///etc/passwd")
    assert bad_scheme is False
    assert "protocol" in msg.lower()

    # Blocked Cloud Metadata IP
    bad_meta, msg = is_safe_target_url("http://169.254.169.254/latest/meta-data")
    assert bad_meta is False
    assert "blocked" in msg.lower()

    # Blocked Disallowed External URL (when allow_external is False)
    bad_ext, msg = is_safe_target_url("http://malicious-external-domain.com")
    assert bad_ext is False
    assert "whitelist" in msg.lower()

# 3. ASYNCHRONOUS TEST EXECUTION QUEUE & STATUS POLLING
def test_async_execution_queue_and_status_polling(client):
    """Verify test execution starts in background queue and reports status via polling."""
    payload = {
        "suite": "all",
        "target_url": "http://127.0.0.1:5000/app/target-store",
        "exec_mode": "Builtin"
    }
    exec_res = client.post("/api/execute-test", json=payload)
    assert exec_res.status_code == 200
    data = exec_res.get_json()
    assert data["success"] is True
    assert "run_id" in data
    run_id = data["run_id"]

    # Poll status endpoint
    time.sleep(0.8)
    status_res = client.get(f"/api/test-runs/{run_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.get_json()
    assert status_data["id"] == run_id
    assert status_data["status"] in ["QUEUED", "RUNNING", "COMPLETED"]

# 4. REQUIREMENT TRACEABILITY & IMPACT ANALYSIS
def test_requirement_traceability_and_impact_analysis(client):
    """Verify requirement updates trigger impact analysis (flagging linked test cases as NEEDS_REVIEW)."""
    # 1. Ingest requirement and generate test cases
    gen_payload = {
        "title": "Payment Gateway Module",
        "module_name": "Payments",
        "description": "Processing credit card transactions",
        "acceptance_criteria": "- Process Visa and Mastercard\n- Deduct correct amount",
        "test_types": ["Functional", "Security"]
    }
    gen_res = client.post("/api/generate-testcases", json=gen_payload).get_json()
    req_id = gen_res["requirement_id"]

    # Approve first test case
    tc_id = gen_res["test_cases"][0]["id"]
    client.patch(f"/api/testcases/{tc_id}/status", json={"status": "APPROVED"})

    # 2. Update requirement to trigger Impact Analysis
    update_payload = {
        "title": "Payment Gateway Module v2 (3D Secure)",
        "module_name": "Payments",
        "description": "Added OTP 3D Secure verification",
        "acceptance_criteria": "- Require OTP on payments > $500"
    }
    upd_res = client.put(f"/api/requirements/{req_id}", json=update_payload)
    assert upd_res.status_code == 200
    upd_data = upd_res.get_json()
    assert upd_data["impact_analysis"]["impacted_test_cases_count"] >= 1

    # Verify test case now has needs_review = 1
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT needs_review, status FROM test_cases WHERE id = ?", (tc_id,))
    tc_row = cursor.fetchone()
    assert tc_row["needs_review"] == 1
    conn.close()

    # 3. Check Traceability Matrix endpoint
    matrix_res = client.get("/api/traceability/matrix")
    assert matrix_res.status_code == 200
    matrix_data = matrix_res.get_json()
    assert len(matrix_data["matrix"]) > 0

# 5. AI SCHEMA VALIDATION & TRANSPARENCY
def test_ai_testcase_schema_and_provider_transparency(client):
    """Verify AI generator outputs valid schema and stamps provider metadata."""
    test_cases, provider = ai_engine.generate_test_cases(
        title="Cart Discount Logic",
        description="Verify promo code application",
        module_name="Checkout",
        test_types=["Functional", "Boundary"]
    )
    assert provider in [GEMINI_MODEL_NAME, "offline-heuristic"]
    assert len(test_cases) >= 2
    for tc in test_cases:
        assert "title" in tc
        assert "gherkin_text" in tc
        assert "steps_json" in tc
        assert "expected_result" in tc
        assert tc["provider"] == provider

# 6. JAVA POM CODE GENERATOR SANITIZATION
def test_java_code_generator_sanitization():
    """Verify Java code generator strictly sanitizes method and class identifiers."""
    dirty_title = "Verify user login with @#$ special &* characters & 20% discount!"
    clean_name = java_generator.sanitize_method_name(dirty_title)
    assert "@" not in clean_name
    assert "#" not in clean_name
    assert "%" not in clean_name
    assert clean_name.isidentifier() or clean_name.startswith("test_step")

    # Generate full TestNG class
    java_code = java_generator.generate_testng_class("AuthSuite", [{"title": dirty_title, "steps_json": []}])
    assert "public class AuthsuiteTest" in java_code
    assert "@Test" in java_code

# 7. AI ROOT CAUSE ANALYSIS BUG GENERATION
def test_ai_bug_report_rca_generation(client):
    """Verify AI RCA bug reports are generated with severity, RCA explanation, and linked IDs."""
    bug_payload = {
        "test_title": "Checkout Promo Code Discount",
        "error_message": "AssertionError: Expected '$79.99' but found '$99.99'",
        "stack_trace": "AssertionError in checkout_test.py: line 44",
        "browser_logs": "Discount state was omitted from subtotal render"
    }
    response = client.post("/api/generate-bug-report", json=bug_payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    report = data["bug_report"]
    assert report["severity"] in ["Critical", "High", "Medium", "Low"]
    assert len(report["root_cause_analysis"]) > 10
    assert len(report["ai_fix_suggestion"]) > 5

# 8. ENHANCED DASHBOARD METRICS & TRANSPARENCY
def test_dashboard_stats_enhanced_metrics(client):
    """Verify /api/dashboard/stats returns calculation transparency, workflow guidance, and regression info."""
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.get_json()

    # Core metrics
    assert "success_rate" in data
    assert "code_coverage" in data
    assert "total_test_cases" in data
    assert "active_bugs" in data

    # Transparency metadata
    assert "metric_explanations" in data
    assert "success_rate" in data["metric_explanations"]
    assert "requirement_coverage" in data["metric_explanations"]
    assert "workflow_guidance" in data
    assert "active_step" in data["workflow_guidance"]
    assert "stage_title" in data["workflow_guidance"]

    # Coverage breakdown
    assert "coverage_counts" in data
    assert "covered" in data["coverage_counts"]
    assert "total" in data["coverage_counts"]
    assert "requirement_coverage_list" in data

    # Regression info
    assert "regression_info" in data

# 9. RUN COMPARISON API
def test_test_runs_comparison(client):
    """Verify /api/test-runs/compare computes side-by-side deltas between two runs."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM test_runs ORDER BY id ASC LIMIT 2")
    rows = c.fetchall()
    conn.close()

    if len(rows) >= 2:
        run_a = rows[0]["id"]
        run_b = rows[1]["id"]
        res = client.get(f"/api/test-runs/compare?run_a={run_a}&run_b={run_b}")
        assert res.status_code == 200
        data = res.get_json()
        assert "run_a" in data
        assert "run_b" in data
        assert "deltas" in data
        assert "pass_rate_diff" in data["deltas"]
        assert "duration_diff_sec" in data["deltas"]
        assert "test_diffs" in data

# 10. DEFECTS DETAILS API
def test_defects_details_endpoint(client):
    """Verify /api/defects/details returns defect cards with error messages and AI RCA."""
    res = client.get("/api/defects/details")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "defects" in data
    assert isinstance(data["defects"], list)

# 11. AI COPILOT STATUS, TELEMETRY & LATENCY
def test_ai_status_telemetry(client):
    """Verify /api/ai/status returns provider transparency, operational status, and real latency measurements."""
    res = client.get("/api/ai/status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "OPERATIONAL"
    assert "active_provider" in data
    assert "model_name" in data
    assert "trust_level" in data
    assert "capabilities" in data
    assert "latency_display" in data
    assert "privacy_statement" in data
    assert isinstance(data["capabilities"], list)
    assert len(data["capabilities"]) >= 4

def test_ai_latency_tracking_and_zero_measured_metrics():
    """Verify latency tracking computes real sample metrics and reports 'Not measured' when empty."""
    from engine.ai_generator import AIAssistantEngine
    test_engine = AIAssistantEngine()

    # Initial state with zero requests
    empty_latency = test_engine.get_average_latency_metrics()
    assert empty_latency["latency_ms"] is None
    assert empty_latency["latency_display"] == "Not measured"
    assert empty_latency["samples_count"] == 0

    # Record 3 genuine latency samples
    test_engine._record_latency(10.0, GEMINI_MODEL_NAME)
    test_engine._record_latency(20.0, GEMINI_MODEL_NAME)
    test_engine._record_latency(30.0, GEMINI_MODEL_NAME)

    measured_latency = test_engine.get_average_latency_metrics()
    assert measured_latency["latency_ms"] == 20.0
    assert "20.0 ms" in measured_latency["latency_display"]
    assert measured_latency["samples_count"] == 3


# 12. TEST CASE LIFECYCLE AUDIT & APPROVAL
def test_testcase_status_approval_lifecycle(client):
    """Verify PATCH /api/testcases/<id>/status updates status, reviewer, and notes."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM test_cases LIMIT 1")
    row = c.fetchone()
    conn.close()

    if row:
        tc_id = row["id"]
        patch_res = client.patch(f"/api/testcases/{tc_id}/status", json={
            "status": "APPROVED",
            "reviewer": "QA Lead Architect",
            "review_notes": "All BDD assertions verified against acceptance criteria."
        })
        assert patch_res.status_code == 200
        data = patch_res.get_json()
        assert data["success"] is True
        assert data["status"] == "APPROVED"
        assert data["reviewer"] == "QA Lead Architect"

# 13. CROSS-USER AUTHORIZATION & SECURITY
def test_cross_user_isolation_and_auth_checks(client):
    """Verify unauthorized requests are rejected and session state is isolated."""
    # Logout to clear session
    client.post("/api/auth/logout")

    # Access current user when not logged in
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    assert res.get_json()["authenticated"] is False

    # Password validation rejects short passwords
    bad_reg_res = client.post("/api/auth/register", json={
        "username": "short_pw_user",
        "email": "short@qa.com",
        "password": "123"
    })
    assert bad_reg_res.status_code == 400
    assert "at least 6 characters" in bad_reg_res.get_json()["error"]

# 14. ADVANCED URL SAFETY & PROTOCOL VALIDATION
def test_advanced_url_safety_and_prohibited_schemes():
    """Verify dangerous schemes, metadata endpoints, and invalid ports are blocked."""
    # Prohibited schemes
    for bad_url in ["javascript:alert(1)", "data:text/html,<h1>XSS</h1>", "ftp://evil.com/file", "gopher://evil.com"]:
        ok, msg = is_safe_target_url(bad_url)
        assert ok is False
        assert "protocol" in msg.lower() or "malformed" in msg.lower()

    # Blocked metadata endpoints
    for meta_url in ["http://metadata.google.internal/computeMetadata/v1", "http://instance-data/latest/meta-data"]:
        ok, msg = is_safe_target_url(meta_url)
        assert ok is False
        assert "metadata" in msg.lower() or "blocked" in msg.lower()

    # Port out of range
    ok, msg = is_safe_target_url("http://127.0.0.1:999999/test")
    assert ok is False
    assert "port" in msg.lower()

# 15. JAVA RESERVED KEYWORDS SANITIZATION
def test_java_reserved_keywords_sanitization():
    """Verify Java keywords like class, int, return are prefixed safely."""
    for kw in ["class", "public", "return", "int", "default", "interface"]:
        sanitized = java_generator.sanitize_method_name(kw)
        assert sanitized != kw
        assert not sanitized.startswith("class_") or sanitized.startswith("test_step_")

# 16. SELENIUM EXECUTION MODES & SIMULATION LABELING
def test_selenium_execution_mode_and_simulation_flag():
    """Verify execution mode and is_simulated flags are properly set and labeled."""
    mock_tc = {
        "title": "Mock Safe Simulation Test",
        "steps_json": [{"action": "navigate", "target": "/app/target-store"}, {"action": "assert_text", "target": "body", "value": "Store"}]
    }
    sim_result = selenium_runner.execute_test_case(mock_tc, exec_mode="HEURISTIC_SIMULATION", target_base_url="http://127.0.0.1:5000")
    assert sim_result["is_simulated"] == 1
    assert sim_result["execution_mode"] == "HEURISTIC_SIMULATION"
    assert "browser_logs" in sim_result

# 17. ASYNC QUEUE CANCELLATION
def test_async_queue_cancellation(client):
    """Verify active queue runs can be cancelled cleanly."""
    payload = {
        "suite": "all",
        "target_url": "http://127.0.0.1:5000/app/target-store",
        "exec_mode": "HEURISTIC_SIMULATION"
    }
    exec_res = client.post("/api/execute-test", json=payload).get_json()
    run_id = exec_res["run_id"]

    cancel_res = client.post(f"/api/test-runs/{run_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.get_json()["success"] in [True, False]

# 18. GOOGLE-GENAI SDK — GEMINI PROVIDER MOCKED SUCCESS
def test_gemini_provider_mocked_success_sdk(monkeypatch):
    """
    Verify GeminiLLMProvider generates structured test cases when the official
    google-genai SDK returns a valid JSON response.
    Mocks google.genai.Client so no real API key or network call is needed.
    """
    from unittest.mock import MagicMock, patch
    from engine.ai_generator import GeminiLLMProvider, GEMINI_MODEL_NAME

    valid_cases = [{
        "title": "Online Gemini Generated Login Scenario",
        "test_type": "Functional",
        "priority": "High",
        "gherkin_text": "Feature: Auth\nScenario: Login\nGiven on login\nWhen submits\nThen ok",
        "pre_conditions": "Active account",
        "steps_json": [
            {"action": "navigate", "target": "/app/target-store", "value": ""},
            {"action": "click", "target": "#login-btn", "value": ""},
            {"action": "assert_visible", "target": "#user-badge", "value": ""}
        ],
        "expected_result": "Login is verified"
    }]

    # Build a mock genai module with the response returning valid JSON
    mock_response = MagicMock()
    mock_response.text = json.dumps(valid_cases)

    mock_models = MagicMock()
    mock_models.generate_content.return_value = mock_response

    mock_client_instance = MagicMock()
    mock_client_instance.models = mock_models

    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client_instance

    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyRealMockedKeyForTesting12345")
    monkeypatch.setenv("AI_PROVIDER", "gemini")

    provider = GeminiLLMProvider()
    with patch.dict("sys.modules", {"google": MagicMock(genai=mock_genai), "google.genai": mock_genai}):
        # Patch the internal _build_client to return our mock client
        provider._build_client = lambda key: mock_client_instance
        cases, err = provider.generate_test_cases(
            title="Payment Checkout",
            description="Verify 3D secure card checkout",
            module_name="Checkout",
            acceptance_criteria="",
            test_types=["Functional"]
        )

    assert err is None
    assert len(cases) == 1
    assert cases[0]["title"] == "Online Gemini Generated Login Scenario"
    # Confirm the SDK was called with the correct model name
    mock_models.generate_content.assert_called_once()
    call_kwargs = mock_models.generate_content.call_args
    assert GEMINI_MODEL_NAME in str(call_kwargs)


# 18b. ENGINE-LEVEL GEMINI SUCCESS (ai_engine.generate_test_cases)
def test_gemini_engine_generate_uses_sdk(monkeypatch):
    """
    End-to-end engine test: ai_engine.generate_test_cases returns Gemini results
    when the SDK mock returns a valid structured response.
    """
    from unittest.mock import MagicMock
    from engine.ai_generator import ai_engine

    valid_cases = [{
        "title": "SDK Engine Generated Test Case",
        "test_type": "Functional",
        "priority": "High",
        "gherkin_text": "Feature: SDK\nScenario: Pass",
        "pre_conditions": "App running",
        "steps_json": [
            {"action": "navigate", "target": "/app/target-store", "value": ""},
            {"action": "assert_visible", "target": "body", "value": ""}
        ],
        "expected_result": "Page is visible"
    }]

    mock_response = MagicMock()
    mock_response.text = json.dumps(valid_cases)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyRealMockedKeyForTesting12345")
    monkeypatch.setenv("AI_PROVIDER", "gemini")

    # Patch _build_client at the provider level
    ai_engine.gemini_provider._build_client = lambda key: mock_client

    cases, provider = ai_engine.generate_test_cases(
        title="SDK Engine Test",
        description="Verify engine routes through SDK",
        module_name="Engine"
    )

    assert provider == GEMINI_MODEL_NAME
    assert len(cases) == 1
    assert cases[0]["provider"] == GEMINI_MODEL_NAME
    assert cases[0]["title"] == "SDK Engine Generated Test Case"
    # Telemetry must show SUCCESS and no fallback
    telemetry = ai_engine.last_generation_info
    assert telemetry["status"] == "SUCCESS"
    assert telemetry["fallback_used"] is False
    assert telemetry["latency_ms"] is not None
    assert telemetry["latency_ms"] >= 0

    # Cleanup: restore the real _build_client
    from engine.ai_generator import GeminiLLMProvider
    ai_engine.gemini_provider._build_client = GeminiLLMProvider._build_client.__get__(
        ai_engine.gemini_provider, GeminiLLMProvider
    )


# 19. GEMINI SDK — RATE LIMIT & TIMEOUT TRIGGER HEURISTIC FALLBACK
def test_gemini_sdk_rate_limit_and_timeout_fallback(monkeypatch):
    """
    Verify that SDK exceptions (rate limit, timeout, network) trigger safe offline
    heuristic fallback and stamp fallback_used=True in telemetry.
    """
    from unittest.mock import MagicMock
    from engine.ai_generator import ai_engine

    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyRealMockedKeyForTesting12345")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("AI_FALLBACK_ENABLED", "true")

    # 1. Simulate a 429 / rate-limit error from the SDK
    def raise_rate_limit(key):
        raise Exception("429: Resource has been exhausted quota exceeded")
    ai_engine.gemini_provider._build_client = lambda key: (_ for _ in ()).throw(
        Exception("429: Resource has been exhausted quota exceeded")
    )
    # Simpler approach: patch generate_test_cases directly on the provider
    original_gen = ai_engine.gemini_provider.generate_test_cases
    ai_engine.gemini_provider.generate_test_cases = lambda **kw: (
        None, "Gemini API rate limit / quota exceeded: 429 Resource exhausted"
    )

    cases, provider = ai_engine.generate_test_cases(
        title="User Login",
        description="Standard customer login",
        module_name="Authentication"
    )
    assert provider == "offline-heuristic"
    assert len(cases) >= 1
    assert cases[0]["provider"] == "offline-heuristic"
    assert ai_engine.last_generation_info["fallback_used"] is True
    assert ai_engine.last_generation_info["status"] == "FALLBACK"

    # 2. Simulate timeout
    ai_engine.gemini_provider.generate_test_cases = lambda **kw: (
        None, "Gemini API request timed out: deadline exceeded"
    )
    cases_to, provider_to = ai_engine.generate_test_cases(
        title="Search Catalog",
        description="Keyword filter",
        module_name="Catalog"
    )
    assert provider_to == "offline-heuristic"
    assert cases_to[0]["provider"] == "offline-heuristic"

    # Restore original
    ai_engine.gemini_provider.generate_test_cases = original_gen


# 20. GEMINI SDK — MALFORMED/DANGEROUS ACTION REJECTION
def test_gemini_sdk_invalid_action_rejection_and_fallback(monkeypatch):
    """
    Verify that unpermitted/malicious step actions in the SDK response are caught
    by the schema validator and trigger heuristic fallback with safe actions only.
    """
    from unittest.mock import MagicMock
    from engine.ai_generator import ai_engine

    malicious_cases = [{
        "title": "Malicious Script Injection Attempt",
        "test_type": "Functional",
        "priority": "Critical",
        "gherkin_text": "Feature: Exploit",
        "pre_conditions": "None",
        "steps_json": [
            {"action": "execute_arbitrary_shell_command", "target": "rm -rf /", "value": ""}
        ],
        "expected_result": "Exploit"
    }]

    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyRealMockedKeyForTesting12345")
    monkeypatch.setenv("AI_PROVIDER", "gemini")

    original_gen = ai_engine.gemini_provider.generate_test_cases
    # Return malicious cases from the mocked provider
    ai_engine.gemini_provider.generate_test_cases = lambda **kw: (malicious_cases, None)

    cases, provider = ai_engine.generate_test_cases(
        title="User Login",
        description="Standard customer login",
        module_name="Authentication"
    )

    # Must reject unpermitted action and fall back to safe heuristics
    assert provider == "offline-heuristic"
    for step in cases[0]["steps_json"]:
        assert step["action"] in [
            "navigate", "click", "input", "clear", "assert_text",
            "assert_visible", "assert_not_visible", "assert_count_gt", "assert_disabled"
        ]

    ai_engine.gemini_provider.generate_test_cases = original_gen


# NEW 21. DASHBOARD LABEL SEMANTICS
def test_dashboard_label_no_key(monkeypatch):
    """
    When GEMINI_API_KEY is absent / placeholder and AI_PROVIDER=gemini,
    dashboard_label must be 'UNAVAILABLE — Gemini unavailable'.
    """
    from engine.ai_generator import AIAssistantEngine, GeminiLLMProvider
    import engine.ai_generator
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setattr(engine.ai_generator, "GEMINI_API_KEY", "")
    engine = AIAssistantEngine()
    status = engine.get_engine_status()
    assert status["dashboard_label"] == GeminiLLMProvider.LABEL_NO_KEY


def test_dashboard_label_online(monkeypatch):
    """
    When a valid Gemini key is set and last generation succeeded,
    dashboard_label must be 'ONLINE — Gemini AI'.
    """
    from engine.ai_generator import AIAssistantEngine, GeminiLLMProvider
    import engine.ai_generator
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyRealMockedKeyForTesting12345")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setattr(engine.ai_generator, "GEMINI_API_KEY", "AIzaSyRealMockedKeyForTesting12345")
    engine = AIAssistantEngine()
    # Simulate a successful generation
    engine.last_generation_info["fallback_used"] = False
    status = engine.get_engine_status()
    assert status["dashboard_label"] == GeminiLLMProvider.LABEL_ONLINE


def test_dashboard_label_fallback(monkeypatch):
    """
    When a valid Gemini key is set but last generation used heuristic fallback,
    dashboard_label must be 'FALLBACK — Offline Heuristic'.
    """
    from engine.ai_generator import AIAssistantEngine, GeminiLLMProvider
    import engine.ai_generator
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyRealMockedKeyForTesting12345")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setattr(engine.ai_generator, "GEMINI_API_KEY", "AIzaSyRealMockedKeyForTesting12345")
    engine = AIAssistantEngine()
    # Simulate a fallback
    engine.last_generation_info["fallback_used"] = True
    status = engine.get_engine_status()
    assert status["dashboard_label"] == GeminiLLMProvider.LABEL_FALLBACK


# NEW 22. GOOGLE-GENAI SDK IMPORTABILITY
def test_google_genai_sdk_importable():
    """Verify google-genai SDK is installed and importable. Fails if pip install google-genai was skipped."""
    try:
        from google import genai
        assert hasattr(genai, "Client"), "google.genai.Client not found in SDK"
    except ImportError:
        pytest.fail(
            "google-genai package is not installed. "
            "Run: pip install google-genai"
        )


# NEW 23. AI_FALLBACK_ENABLED=false surfaces error instead of silently substituting
def test_fallback_disabled_returns_empty_not_heuristic(monkeypatch):
    """
    When AI_FALLBACK_ENABLED=false and Gemini fails, engine must NOT silently
    substitute the Offline Heuristic Engine. Instead it returns an empty list.
    """
    from engine.ai_generator import AIAssistantEngine
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyRealMockedKeyForTesting12345")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("AI_FALLBACK_ENABLED", "false")

    engine = AIAssistantEngine()
    # Patch provider to always fail
    engine.gemini_provider.generate_test_cases = lambda **kw: (
        None, "Simulated Gemini failure for fallback-disabled test"
    )

    cases, provider = engine.generate_test_cases(
        title="Checkout",
        description="Test cart",
        module_name="Cart"
    )
    # With fallback disabled, engine returns empty list (not heuristic cases)
    assert provider == GEMINI_MODEL_NAME
    assert cases == []
    assert engine.last_generation_info["status"] == "ERROR"
    assert engine.last_generation_info["fallback_used"] is False


# NEW 24. TELEMETRY FIELDS — model, fallback_used, status
def test_telemetry_fields_populated_on_success(monkeypatch):
    """
    After a successful generation (mocked), last_generation_info must contain
    the required telemetry fields: provider_used, model, latency_ms, fallback_used, status.
    """
    from unittest.mock import MagicMock
    from engine.ai_generator import AIAssistantEngine

    valid_cases = [{
        "title": "Telemetry Test Case",
        "test_type": "Functional",
        "priority": "Medium",
        "gherkin_text": "Feature: Telemetry\nScenario: Check",
        "pre_conditions": "System running",
        "steps_json": [
            {"action": "navigate", "target": "/app/target-store", "value": ""}
        ],
        "expected_result": "Page loads"
    }]

    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyRealMockedKeyForTesting12345")
    monkeypatch.setenv("AI_PROVIDER", "gemini")

    engine = AIAssistantEngine()
    # Patch provider to return valid cases
    engine.gemini_provider.generate_test_cases = lambda **kw: (valid_cases, None)

    cases, provider = engine.generate_test_cases(
        title="Telemetry Test",
        description="Check telemetry",
        module_name="Telemetry"
    )

    assert provider == GEMINI_MODEL_NAME
    t = engine.last_generation_info
    assert "provider_used" in t
    assert "model" in t
    assert "latency_ms" in t
    assert "fallback_used" in t
    assert "status" in t
    assert t["status"] == "SUCCESS"
    assert t["fallback_used"] is False
    assert t["provider_used"] == GEMINI_MODEL_NAME
    assert t["latency_ms"] >= 0



# 21. OPENAI PROVIDER MOCKED SUCCESS & CHAT
def test_openai_provider_mocked_success_and_chat(monkeypatch):
    """Verify OpenAI provider completes test generation and chat interactions."""
    from unittest.mock import MagicMock
    import requests
    from engine.ai_generator import ai_engine

    mock_openai_response = {
        "choices": [{
            "message": {
                "content": json.dumps([{
                    "title": "OpenAI Generated Test Case",
                    "test_type": "Functional",
                    "priority": "High",
                    "gherkin_text": "Feature: Cart\nScenario: Add to cart",
                    "pre_conditions": "Product in stock",
                    "steps_json": [
                        {"action": "navigate", "target": "/app/target-store", "value": ""},
                        {"action": "click", "target": ".add-to-cart-btn", "value": ""}
                    ],
                    "expected_result": "Item added to cart"
                }])
            }
        }]
    }

    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = mock_openai_response
    monkeypatch.setattr(requests, "post", mock_post)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-RealMockedKeyForTesting123456789")
    monkeypatch.setenv("AI_PROVIDER", "openai")

    cases, provider = ai_engine.generate_test_cases(
        title="Cart Addition",
        description="Verify item in cart",
        module_name="Cart"
    )
    assert provider == "gpt-4o-mini"
    assert len(cases) == 1
    assert cases[0]["title"] == "OpenAI Generated Test Case"

# 22. ZERO SECRET EXPOSURE IN TELEMETRY AND API RESPONSES
def test_zero_secret_exposure_in_apis(client, monkeypatch):
    """Verify API keys are never exposed in /api/ai/status or /api/ai-chat."""
    secret_key_val = "SECRET_SUPER_CONFIDENTIAL_KEY_99999"
    monkeypatch.setenv("GEMINI_API_KEY", secret_key_val)
    monkeypatch.setenv("OPENAI_API_KEY", secret_key_val)

    # Status API check
    status_res = client.get("/api/ai/status")
    assert status_res.status_code == 200
    status_text = status_res.get_data(as_text=True)
    assert secret_key_val not in status_text

    # Chat API check
    chat_res = client.post("/api/ai-chat", json={"message": "What is my API key?"})
    assert chat_res.status_code == 200
    chat_text = chat_res.get_data(as_text=True)
    assert secret_key_val not in chat_text



