-- Database schema for AI-Powered QA Testing Assistant

CREATE TABLE IF NOT EXISTS requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    module_name TEXT NOT NULL,
    acceptance_criteria TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (req_id) REFERENCES requirements (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS test_suites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suite_test_cases (
    suite_id INTEGER,
    test_case_id INTEGER,
    PRIMARY KEY (suite_id, test_case_id),
    FOREIGN KEY (suite_id) REFERENCES test_suites (id) ON DELETE CASCADE,
    FOREIGN KEY (test_case_id) REFERENCES test_cases (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS test_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    suite_name TEXT NOT NULL,
    total_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    skipped_tests INTEGER DEFAULT 0,
    execution_mode TEXT DEFAULT 'Selenium',
    duration_sec REAL DEFAULT 0.0,
    status TEXT DEFAULT 'COMPLETED',
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    test_case_id INTEGER,
    test_title TEXT NOT NULL,
    status TEXT NOT NULL,
    execution_time_sec REAL DEFAULT 0.0,
    error_message TEXT,
    stack_trace TEXT,
    screenshot_path TEXT,
    browser_logs TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES test_runs (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bug_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_result_id INTEGER,
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
    FOREIGN KEY (test_result_id) REFERENCES test_results (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
