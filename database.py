import sqlite3
import json
from werkzeug.security import generate_password_hash
from config import DATABASE_PATH

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT DEFAULT 'Tester',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Requirements Table (with versioning & status)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        module_name TEXT NOT NULL,
        acceptance_criteria TEXT,
        version INTEGER DEFAULT 1,
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Test Cases Table (with needs_review impact flag & requirement linking)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        req_id INTEGER,
        title TEXT NOT NULL,
        test_type TEXT DEFAULT 'Functional',
        priority TEXT DEFAULT 'Medium',
        gherkin_text TEXT,
        pre_conditions TEXT,
        steps_json TEXT,
        expected_result TEXT,
        status TEXT DEFAULT 'DRAFT',
        needs_review INTEGER DEFAULT 0,
        provider TEXT DEFAULT 'heuristic',
        reviewer TEXT,
        review_notes TEXT,
        reviewed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (req_id) REFERENCES requirements (id) ON DELETE SET NULL
    )
    """)

    # Test Suites Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_suites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Suite Test Cases Mapping
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suite_test_cases (
        suite_id INTEGER,
        test_case_id INTEGER,
        PRIMARY KEY (suite_id, test_case_id),
        FOREIGN KEY (suite_id) REFERENCES test_suites (id) ON DELETE CASCADE,
        FOREIGN KEY (test_case_id) REFERENCES test_cases (id) ON DELETE CASCADE
    )
    """)

    # Test Runs Table (Asynchronous queue states & is_simulated flag)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        suite_name TEXT NOT NULL,
        total_tests INTEGER DEFAULT 0,
        passed_tests INTEGER DEFAULT 0,
        failed_tests INTEGER DEFAULT 0,
        skipped_tests INTEGER DEFAULT 0,
        execution_mode TEXT DEFAULT 'Selenium',
        is_simulated INTEGER DEFAULT 0,
        duration_sec REAL DEFAULT 0.0,
        status TEXT DEFAULT 'QUEUED',
        error_summary TEXT,
        browser TEXT DEFAULT 'Chrome Headless (v124)',
        environment TEXT DEFAULT 'Windows 64-bit / Localhost',
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Test Results Table (Linked to requirement & test case)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        test_case_id INTEGER,
        req_id INTEGER,
        test_title TEXT NOT NULL,
        status TEXT NOT NULL,
        execution_time_sec REAL DEFAULT 0.0,
        error_message TEXT,
        stack_trace TEXT,
        screenshot_path TEXT,
        browser_logs TEXT,
        is_simulated INTEGER DEFAULT 0,
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (run_id) REFERENCES test_runs (id) ON DELETE CASCADE,
        FOREIGN KEY (test_case_id) REFERENCES test_cases (id) ON DELETE SET NULL,
        FOREIGN KEY (req_id) REFERENCES requirements (id) ON DELETE SET NULL
    )
    """)

    # Bug Reports Table (Direct traceability to test result & requirement)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bug_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_result_id INTEGER,
        req_id INTEGER,
        test_case_id INTEGER,
        title TEXT NOT NULL,
        severity TEXT DEFAULT 'Medium',
        module TEXT NOT NULL,
        summary TEXT,
        steps_to_reproduce TEXT,
        actual_result TEXT,
        expected_result TEXT,
        root_cause_analysis TEXT,
        ai_fix_suggestion TEXT,
        status TEXT DEFAULT 'OPEN',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (test_result_id) REFERENCES test_results (id) ON DELETE SET NULL,
        FOREIGN KEY (req_id) REFERENCES requirements (id) ON DELETE SET NULL,
        FOREIGN KEY (test_case_id) REFERENCES test_cases (id) ON DELETE SET NULL
    )
    """)

    # Settings / Config table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # Column Migrations for existing databases
    cursor.execute("PRAGMA table_info(requirements)")
    req_cols = [row[1] for row in cursor.fetchall()]
    if "version" not in req_cols:
        cursor.execute("ALTER TABLE requirements ADD COLUMN version INTEGER DEFAULT 1")
    if "status" not in req_cols:
        cursor.execute("ALTER TABLE requirements ADD COLUMN status TEXT DEFAULT 'ACTIVE'")
    if "updated_at" not in req_cols:
        cursor.execute("ALTER TABLE requirements ADD COLUMN updated_at TIMESTAMP")

    cursor.execute("PRAGMA table_info(test_cases)")
    tc_cols = [row[1] for row in cursor.fetchall()]
    if "needs_review" not in tc_cols:
        cursor.execute("ALTER TABLE test_cases ADD COLUMN needs_review INTEGER DEFAULT 0")
    if "provider" not in tc_cols:
        cursor.execute("ALTER TABLE test_cases ADD COLUMN provider TEXT DEFAULT 'heuristic'")
    if "reviewer" not in tc_cols:
        cursor.execute("ALTER TABLE test_cases ADD COLUMN reviewer TEXT")
    if "review_notes" not in tc_cols:
        cursor.execute("ALTER TABLE test_cases ADD COLUMN review_notes TEXT")
    if "reviewed_at" not in tc_cols:
        cursor.execute("ALTER TABLE test_cases ADD COLUMN reviewed_at TIMESTAMP")

    cursor.execute("PRAGMA table_info(test_runs)")
    run_cols = [row[1] for row in cursor.fetchall()]
    if "is_simulated" not in run_cols:
        cursor.execute("ALTER TABLE test_runs ADD COLUMN is_simulated INTEGER DEFAULT 0")
    if "error_summary" not in run_cols:
        cursor.execute("ALTER TABLE test_runs ADD COLUMN error_summary TEXT")
    if "browser" not in run_cols:
        cursor.execute("ALTER TABLE test_runs ADD COLUMN browser TEXT DEFAULT 'Chrome Headless (v124)'")
    if "environment" not in run_cols:
        cursor.execute("ALTER TABLE test_runs ADD COLUMN environment TEXT DEFAULT 'Windows 64-bit / Localhost'")

    cursor.execute("PRAGMA table_info(test_results)")
    res_cols = [row[1] for row in cursor.fetchall()]
    if "req_id" not in res_cols:
        cursor.execute("ALTER TABLE test_results ADD COLUMN req_id INTEGER")
    if "is_simulated" not in res_cols:
        cursor.execute("ALTER TABLE test_results ADD COLUMN is_simulated INTEGER DEFAULT 0")

    cursor.execute("PRAGMA table_info(bug_reports)")
    bug_cols = [row[1] for row in cursor.fetchall()]
    if "req_id" not in bug_cols:
        cursor.execute("ALTER TABLE bug_reports ADD COLUMN req_id INTEGER")
    if "test_case_id" not in bug_cols:
        cursor.execute("ALTER TABLE bug_reports ADD COLUMN test_case_id INTEGER")

    # Terminology and reviewer normalization
    cursor.execute("UPDATE test_runs SET execution_mode = 'Real Selenium WebDriver' WHERE execution_mode IN ('Selenium', 'Selenium WebDriver')")
    cursor.execute("UPDATE test_runs SET execution_mode = 'Simulated (In-Memory Engine)' WHERE execution_mode IN ('Built-in Runner', 'Simulated', 'Fast Runner')")
    cursor.execute("UPDATE test_cases SET reviewer = 'Lead QA Architect', reviewed_at = CURRENT_TIMESTAMP WHERE status = 'APPROVED' AND (reviewer IS NULL OR reviewer = '')")

    conn.commit()
    seed_initial_data(conn)
    conn.close()

def seed_initial_data(conn):
    cursor = conn.cursor()
    
    # 1. Seed Default QA Users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_pass_hash = generate_password_hash("Password@123", method="pbkdf2:sha256")
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, full_name, role)
        VALUES (?, ?, ?, ?, ?)
        """, ("admin", "lead.qa@enterprise.io", admin_pass_hash, "Lead QA Architect", "Lead QA"))

    # 2. Seed Requirements
    cursor.execute("SELECT COUNT(*) FROM requirements")
    if cursor.fetchone()[0] == 0:
        req_sql = """
        INSERT INTO requirements (title, description, module_name, acceptance_criteria, version, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor.execute(req_sql, (
            "User Authentication & Login Flow",
            "As a registered customer, I want to securely log in with email and password so I can access my account, saved cart, and order history.",
            "Authentication",
            "- Valid credentials redirect to dashboard\n- Invalid password displays error message\n- Empty inputs show client validation\n- Account locks after 5 consecutive failed attempts",
            1,
            "ACTIVE"
        ))
        req_id_1 = cursor.lastrowid

        cursor.execute(req_sql, (
            "Product Catalog & Real-time Search",
            "As a shopper, I want to search products by keyword and filter by category/price so I can quickly find desired items.",
            "Catalog & Search",
            "- Search returns relevant matching items\n- Empty search query shows warning\n- Price sorting (low-to-high, high-to-low)\n- Zero search results display 'No products found' message",
            1,
            "ACTIVE"
        ))
        req_id_2 = cursor.lastrowid

        cursor.execute(req_sql, (
            "Shopping Cart & Checkout Workflow",
            "As a customer, I want to add products to my cart, apply promo codes, and complete checkout with shipping and payment info.",
            "Checkout",
            "- Add to cart updates item count badge\n- Quantity increment/decrement recalculates total\n- Empty cart prevents checkout\n- Order confirmation receipt with valid Order ID generated",
            1,
            "ACTIVE"
        ))
        req_id_3 = cursor.lastrowid

        # Seed Test Cases with step mappings
        tc_sql = """
        INSERT INTO test_cases (req_id, title, test_type, priority, gherkin_text, pre_conditions, steps_json, expected_result, status, provider)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        tc_1_steps = json.dumps([
            {"action": "navigate", "target": "/app/target-store", "value": ""},
            {"action": "click", "target": "#nav-login-btn", "value": ""},
            {"action": "input", "target": "#login-email", "value": "demo@qa-platform.io"},
            {"action": "input", "target": "#login-password", "value": "Password@123"},
            {"action": "click", "target": "#login-submit-btn", "value": ""},
            {"action": "assert_text", "target": "#user-profile-badge", "value": "Welcome, Demo Tester"}
        ])
        cursor.execute(tc_sql, (
            req_id_1,
            "Successful login with valid credentials",
            "Functional",
            "High",
            "Feature: User Login\n  Scenario: Successful login with valid credentials\n    Given the user is on the login page\n    When the user enters valid username 'demo@qa-platform.io' and password 'Password@123'\n    And clicks on the login button\n    Then the user is redirected to the dashboard with welcome badge",
            "User account 'demo@qa-platform.io' is active and registered",
            tc_1_steps,
            "User is authenticated and dashboard navigation header shows active session badge.",
            "APPROVED",
            "heuristic"
        ))
        tc_id_1 = cursor.lastrowid

        tc_2_steps = json.dumps([
            {"action": "navigate", "target": "/app/target-store", "value": ""},
            {"action": "click", "target": "#nav-login-btn", "value": ""},
            {"action": "input", "target": "#login-email", "value": "demo@qa-platform.io"},
            {"action": "input", "target": "#login-password", "value": "WrongPassword999"},
            {"action": "click", "target": "#login-submit-btn", "value": ""},
            {"action": "assert_visible", "target": "#login-error-alert", "value": "Invalid credentials"}
        ])
        cursor.execute(tc_sql, (
            req_id_1,
            "Login rejection on invalid password",
            "Negative",
            "High",
            "Feature: User Login\n  Scenario: Rejection on invalid password\n    Given the user is on the login page\n    When the user enters valid email 'demo@qa-platform.io' and invalid password 'WrongPassword999'\n    And clicks on the login button\n    Then an error message 'Invalid email or password' is displayed\n    And user remains on the login page",
            "User is on the login dialog",
            tc_2_steps,
            "Error alert with 'Invalid email or password' is displayed; user is not authenticated.",
            "APPROVED",
            "heuristic"
        ))

        tc_3_steps = json.dumps([
            {"action": "navigate", "target": "/app/target-store", "value": ""},
            {"action": "input", "target": "#search-input", "value": "Wireless Headphones"},
            {"action": "click", "target": "#search-btn", "value": ""},
            {"action": "assert_count_gt", "target": ".product-card", "value": "0"}
        ])
        cursor.execute(tc_sql, (
            req_id_2,
            "Search product catalog by keyword",
            "Functional",
            "Medium",
            "Feature: Product Search\n  Scenario: Search with matching keyword\n    Given the customer is on the store homepage\n    When the user searches for 'Wireless Headphones'\n    Then catalog displays products matching 'Wireless Headphones'",
            "Catalog has items loaded",
            tc_3_steps,
            "Matching product cards are displayed in the results grid.",
            "APPROVED",
            "heuristic"
        ))

        tc_4_steps = json.dumps([
            {"action": "navigate", "target": "/app/target-store", "value": ""},
            {"action": "click", "target": ".add-to-cart-btn:first-of-type", "value": ""},
            {"action": "assert_text", "target": "#cart-badge-count", "value": "1"},
            {"action": "click", "target": "#cart-icon-btn", "value": ""},
            {"action": "click", "target": "#checkout-btn", "value": ""},
            {"action": "assert_visible", "target": "#checkout-modal", "value": ""}
        ])
        cursor.execute(tc_sql, (
            req_id_3,
            "Add product to cart and initiate checkout",
            "Functional",
            "High",
            "Feature: Checkout Flow\n  Scenario: Add product to cart and open checkout\n    Given customer browses the product listing\n    When customer clicks 'Add to Cart' on the first item\n    Then cart badge counter increments to 1\n    When customer clicks the Cart icon and proceeds to Checkout\n    Then checkout modal opens with order summary",
            "Store catalog is populated",
            tc_4_steps,
            "Cart counter increments and checkout dialog loads with cart total.",
            "APPROVED",
            "heuristic"
        ))
        tc_id_4 = cursor.lastrowid

        # Seed Test Suite
        cursor.execute("INSERT INTO test_suites (name, description) VALUES (?, ?)", (
            "Regression Smoke Suite - E-Commerce Core",
            "Core end-to-end smoke suite covering Authentication, Product Catalog Search, and Checkout flows."
        ))
        suite_id = cursor.lastrowid

        for tid in [1, 2, 3, 4]:
            cursor.execute("INSERT OR IGNORE INTO suite_test_cases (suite_id, test_case_id) VALUES (?, ?)", (suite_id, tid))

        # Seed initial completed test run
        cursor.execute("""
        INSERT INTO test_runs (suite_name, total_tests, passed_tests, failed_tests, skipped_tests, execution_mode, is_simulated, duration_sec, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("Regression Smoke Suite - E-Commerce Core", 4, 4, 0, 0, "Real Selenium WebDriver", 0, 4.25, "COMPLETED"))

        # Seed default settings
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("ai_model", "Hybrid (Gemini / Heuristic)"))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("browser", "Chrome"))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("per_test_timeout", "15"))

    conn.commit()
