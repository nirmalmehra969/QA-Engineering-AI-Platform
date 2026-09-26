import time
import threading
import concurrent.futures
from database import get_db_connection
from engine.selenium_runner import selenium_runner

class ExecutionQueueManager:
    """
    Manages asynchronous test suite execution in background worker threads,
    preventing HTTP gateway timeouts and enabling real-time status polling, cancellation,
    timeout handling, and durable status persistence.
    """
    def __init__(self, max_workers=2):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.active_jobs = {}  # run_id -> dict
        self.lock = threading.Lock()

    def submit_test_run(self, run_id, suite_name, test_cases, target_url, exec_mode="SELENIUM_HEADLESS", per_test_timeout=15, user_id=None):
        """Enqueues a test suite run job into the background executor."""
        with self.lock:
            self.active_jobs[run_id] = {
                "cancel_requested": False,
                "progress": 0,
                "current_step": "Job Queued",
                "start_time": time.time(),
                "user_id": user_id,
                "status": "QUEUED"
            }

        # Update run status to QUEUED in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE test_runs SET status = 'QUEUED' WHERE id = ?", (run_id,))
        conn.commit()
        conn.close()

        # Submit background task to thread pool
        self.executor.submit(
            self._execute_run_worker,
            run_id, suite_name, test_cases, target_url, exec_mode, per_test_timeout, user_id
        )
        return True

    def request_cancellation(self, run_id, user_id=None):
        """Requests cancellation of a running or queued job with user authorization."""
        with self.lock:
            if run_id in self.active_jobs:
                job = self.active_jobs[run_id]
                if user_id and job.get("user_id") and job.get("user_id") != user_id:
                    return False
                job["cancel_requested"] = True
                job["status"] = "CANCELLED"
                return True
        return False

    def get_job_progress(self, run_id, user_id=None):
        """Retrieves real-time progress for status polling."""
        with self.lock:
            if run_id in self.active_jobs:
                job = self.active_jobs[run_id]
                if user_id and job.get("user_id") and job.get("user_id") != user_id:
                    return None
                return dict(job)
        return None

    def _execute_run_worker(self, run_id, suite_name, test_cases, target_url, exec_mode, per_test_timeout, user_id):
        conn = get_db_connection()
        cursor = conn.cursor()

        with self.lock:
            if run_id in self.active_jobs:
                self.active_jobs[run_id]["status"] = "RUNNING"
                self.active_jobs[run_id]["current_step"] = "Execution Started"

        cursor.execute("UPDATE test_runs SET status = 'RUNNING' WHERE id = ?", (run_id,))
        conn.commit()

        total = len(test_cases)
        passed = 0
        failed = 0
        skipped = 0
        start_time = time.time()
        max_suite_timeout_sec = max(per_test_timeout * max(total, 1) + 30, 60)

        mode_upper = str(exec_mode).upper().strip()
        is_simulated = 1 if ("SIMULAT" in mode_upper or "HEURISTIC" in mode_upper) else 0
        final_status = "COMPLETED"

        try:
            for idx, tc in enumerate(test_cases, 1):
                # Check cancellation token
                with self.lock:
                    if self.active_jobs.get(run_id, {}).get("cancel_requested"):
                        final_status = "CANCELLED"
                        break

                # Check overall suite timeout
                if time.time() - start_time > max_suite_timeout_sec:
                    final_status = "TIMED_OUT"
                    cursor.execute("UPDATE test_runs SET status = 'TIMED_OUT', error_summary = 'Suite execution exceeded maximum timeout limit' WHERE id = ?", (run_id,))
                    conn.commit()
                    break

                with self.lock:
                    if run_id in self.active_jobs:
                        self.active_jobs[run_id]["progress"] = int(((idx - 1) / max(total, 1)) * 100)
                        self.active_jobs[run_id]["current_step"] = f"Executing ({idx}/{total}): {tc.get('title', '')[:35]}"

                # Execute individual test case
                result = selenium_runner.execute_test_case(
                    tc,
                    exec_mode=exec_mode,
                    target_base_url=target_url,
                    timeout_sec=per_test_timeout
                )

                if result["status"] == "PASSED":
                    passed += 1
                elif result["status"] == "FAILED":
                    failed += 1
                else:
                    skipped += 1

                # Record individual test result linked to requirement
                cursor.execute("""
                INSERT INTO test_results (run_id, test_case_id, req_id, test_title, status, execution_time_sec, error_message, stack_trace, screenshot_path, browser_logs, is_simulated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    tc.get("id"),
                    tc.get("req_id"),
                    result["test_title"],
                    result["status"],
                    result["execution_time_sec"],
                    result["error_message"],
                    result["stack_trace"],
                    result["screenshot_path"],
                    result["browser_logs"],
                    is_simulated
                ))
                test_result_id = cursor.lastrowid
                conn.commit()

                # If test failed, create a linked defect report if not already present
                if result["status"] == "FAILED":
                    defect_title = f"Regression: {tc.get('title', 'Test Failure')[:70]}"
                    cursor.execute("""
                    SELECT id FROM bug_reports WHERE test_case_id = ? AND status = 'OPEN'
                    """, (tc.get("id"),))
                    existing_defect = cursor.fetchone()
                    if not existing_defect:
                        cursor.execute("""
                        INSERT INTO bug_reports (test_result_id, req_id, test_case_id, title, severity, module, summary, steps_to_reproduce, actual_result, expected_result, root_cause_analysis, ai_fix_suggestion, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
                        """, (
                            test_result_id,
                            tc.get("req_id"),
                            tc.get("id"),
                            defect_title,
                            tc.get("priority", "High"),
                            tc.get("module_name", "Automation Regression"),
                            result.get("error_message", "Assertion failed on page DOM"),
                            f"1. Navigate to {target_url}\n2. Execute action steps\n3. Verify DOM assertions",
                            result.get("error_message", "Failed assertion"),
                            tc.get("expected_result", "All assertions pass successfully"),
                            f"DOM Assertion failure during {exec_mode} execution: {result.get('error_message', 'Check logs')}",
                            "Inspect element selectors and verify backend response status."
                        ))
                        conn.commit()

            duration = round(time.time() - start_time, 2)

            with self.lock:
                if self.active_jobs.get(run_id, {}).get("cancel_requested"):
                    final_status = "CANCELLED"
                if run_id in self.active_jobs:
                    self.active_jobs[run_id]["progress"] = 100
                    self.active_jobs[run_id]["status"] = final_status
                    self.active_jobs[run_id]["current_step"] = f"Execution Finished ({final_status})"

            cursor.execute("""
            UPDATE test_runs
            SET total_tests = ?, passed_tests = ?, failed_tests = ?, skipped_tests = ?,
                duration_sec = ?, status = ?, is_simulated = ?
            WHERE id = ?
            """, (total, passed, failed, skipped, duration, final_status, is_simulated, run_id))
            conn.commit()

        except Exception as e:
            cursor.execute("UPDATE test_runs SET status = 'FAILED', error_summary = ? WHERE id = ?", (str(e), run_id))
            conn.commit()

        finally:
            with self.lock:
                if run_id in self.active_jobs:
                    del self.active_jobs[run_id]
            conn.close()

execution_queue = ExecutionQueueManager()

