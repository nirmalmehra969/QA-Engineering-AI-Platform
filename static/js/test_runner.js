// Asynchronous Selenium & Fast Runner Client with Polling & Cancellation
class TestRunnerClient {
    constructor() {
        this.runBtn = document.getElementById('btn-start-automation');
        this.cancelBtn = document.getElementById('btn-cancel-automation');
        this.progressBox = document.getElementById('execution-progress-card');
        this.progressFill = document.getElementById('run-progress-fill');
        this.progressStatus = document.getElementById('run-progress-status');
        this.progressPercentage = document.getElementById('run-progress-percentage');
        this.terminalLogs = document.getElementById('runner-terminal-logs');
        this.resultsPanel = document.getElementById('latest-run-results-panel');
        this.resultsTbody = document.getElementById('latest-results-tbody');
        this.runBadges = document.getElementById('latest-run-badges');
        this.clearTermBtn = document.getElementById('btn-clear-terminal');
        this.downloadLogsBtn = document.getElementById('btn-download-logs');
        this.screenshotModal = document.getElementById('screenshot-modal');
        this.closeScreenshotBtn = document.getElementById('close-screenshot-btn');

        this.currentRunId = null;
        this.pollInterval = null;
        this.renderedLogsCount = 0;
        this.init();
    }

    init() {
        this.runBtn?.addEventListener('click', () => this.startExecution());
        this.cancelBtn?.addEventListener('click', () => this.cancelExecution());
        this.clearTermBtn?.addEventListener('click', () => this.clearTerminal());
        this.downloadLogsBtn?.addEventListener('click', () => this.downloadLogs());
        this.closeScreenshotBtn?.addEventListener('click', () => {
            this.screenshotModal.style.display = 'none';
        });
    }

    clearTerminal() {
        this.terminalLogs.innerHTML = '<div class="log-line log-info">[System] Terminal logs cleared. Ready for next background run.</div>';
    }

    downloadLogs() {
        const text = this.terminalLogs.innerText;
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `selenium_execution_logs_${Date.now()}.txt`;
        a.click();
    }

    appendLog(msg, type = 'info') {
        const line = document.createElement('div');
        line.className = `log-line log-${type}`;
        line.textContent = msg;
        this.terminalLogs.appendChild(line);
        this.terminalLogs.scrollTop = this.terminalLogs.scrollHeight;
    }

    async startExecution() {
        const suite = document.getElementById('runner-suite-select')?.value || 'all';
        const targetUrl = document.getElementById('target-url-input')?.value.trim() || 'http://127.0.0.1:5000/app/target-store';
        const execMode = document.querySelector('input[name="exec_mode"]:checked')?.value || 'Selenium';

        this.runBtn.disabled = true;
        this.runBtn.style.display = 'none';
        this.cancelBtn.style.display = 'inline-block';
        this.progressBox.style.display = 'block';
        this.progressFill.style.width = '5%';
        this.progressPercentage.textContent = '5%';
        this.progressStatus.textContent = 'Enqueuing job into background worker...';
        this.renderedLogsCount = 0;

        this.appendLog(`\n======================================================`, 'info');
        this.appendLog(`[${new Date().toLocaleTimeString()}] 🚀 Submitting Job: Suite='${suite}' | Mode='${execMode}'`, 'info');
        this.appendLog(`[${new Date().toLocaleTimeString()}] 🌐 Target URL: ${targetUrl}`, 'info');

        try {
            const res = await fetch('/api/execute-test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    suite: suite,
                    target_url: targetUrl,
                    exec_mode: execMode
                })
            });

            const data = await res.json();
            if (!res.ok) {
                this.appendLog(`[Security/Validation Error] ${data.message || data.error}`, 'error');
                this.finishJobState();
                return;
            }

            this.currentRunId = data.run_id;
            this.appendLog(`[Queue] Run #${this.currentRunId} accepted in QUEUED state. Starting asynchronous polling...`, 'info');

            // Begin Polling Worker Status
            this.pollInterval = setInterval(() => this.pollRunStatus(), 800);

        } catch (err) {
            this.appendLog(`[Error] Failed to connect to test runner API: ${err}`, 'error');
            this.finishJobState();
        }
    }

    async pollRunStatus() {
        if (!this.currentRunId) return;

        try {
            const res = await fetch(`/api/test-runs/${this.currentRunId}/status`);
            if (!res.ok) return;
            const data = await res.json();

            const mem = data.in_memory_progress;
            if (mem) {
                this.progressFill.style.width = `${Math.max(10, mem.progress)}%`;
                this.progressPercentage.textContent = `${Math.max(10, mem.progress)}%`;
                this.progressStatus.textContent = mem.current_step || 'Executing test cases...';
            }

            // Stream new logs
            if (data.results && data.results.length > this.renderedLogsCount) {
                const newResults = data.results.slice(this.renderedLogsCount);
                newResults.forEach(r => {
                    if (r.browser_logs) {
                        r.browser_logs.split('\n').forEach(line => {
                            if (line.includes('FAILED') || line.includes('❌')) {
                                this.appendLog(line, 'error');
                            } else if (line.includes('Passed') || line.includes('✅') || line.includes('🎉')) {
                                this.appendLog(line, 'success');
                            } else {
                                this.appendLog(line, 'info');
                            }
                        });
                    }
                });
                this.renderedLogsCount = data.results.length;
            }

            // Check if job terminated
            if (['COMPLETED', 'CANCELLED', 'FAILED'].includes(data.status)) {
                clearInterval(this.pollInterval);
                this.pollInterval = null;
                this.progressFill.style.width = '100%';
                this.progressPercentage.textContent = '100%';
                this.progressStatus.textContent = `Run ${data.status} in ${data.duration_sec}s (${data.passed_tests} Passed, ${data.failed_tests} Failed)`;

                this.renderLatestResults(data);
                this.finishJobState();

                if (window.app) {
                    window.app.loadDashboardData();
                    window.app.loadTraceabilityMatrix();
                }
            }
        } catch (e) {
            console.error("Polling error:", e);
        }
    }

    async cancelExecution() {
        if (!this.currentRunId) return;
        this.appendLog(`[User] Requesting cancellation of Run #${this.currentRunId}...`, 'error');
        try {
            await fetch(`/api/test-runs/${this.currentRunId}/cancel`, { method: 'POST' });
        } catch (e) {
            console.error("Cancellation error:", e);
        }
    }

    finishJobState() {
        this.runBtn.disabled = false;
        this.runBtn.style.display = 'block';
        this.cancelBtn.style.display = 'none';
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    renderLatestResults(runData) {
        this.resultsPanel.style.display = 'block';
        this.resultsTbody.innerHTML = '';

        const results = runData.results || [];
        const passedCount = runData.passed_tests || 0;
        const failedCount = runData.failed_tests || 0;

        this.runBadges.innerHTML = `
            <span class="badge-tag" style="background:#064e3b;color:#34d399;">✓ ${passedCount} Passed</span>
            <span class="badge-tag" style="background:${failedCount > 0 ? '#7f1d1d' : '#1e293b'};color:${failedCount > 0 ? '#fca5a5' : '#94a3b8'};">
                ${failedCount > 0 ? `✗ ${failedCount} Failed` : '0 Failures'}
            </span>
            <span class="badge-tag">${runData.is_simulated ? '[SIMULATION]' : '[REAL DOM]'}</span>
            <span class="badge-tag">Duration: ${runData.duration_sec}s</span>
        `;

        results.forEach(res => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="badge-status ${res.status.toLowerCase()}">${res.status}</span></td>
                <td><strong>${res.test_title}</strong></td>
                <td>${res.execution_time_sec}s</td>
                <td>
                    ${res.error_message ? `<span style="color:#f87171;font-size:0.8rem;font-family:var(--font-code);">${res.error_message.substring(0, 70)}</span>` : '<span style="color:#34d399;">All assertions met</span>'}
                </td>
                <td>
                    ${res.screenshot_path ? `
                        <button class="btn-xs btn-outline" onclick="testRunner.viewScreenshot('${res.screenshot_path}', '${res.test_title.replace(/'/g, "\\'")}')">📸 Screenshot</button>
                    ` : '<span style="color:#64748b;">N/A</span>'}
                </td>
                <td>
                    ${res.status === 'FAILED' ? `
                        <button class="btn-xs btn-cyan" onclick="testRunner.generateRCA(${res.id || 0}, ${res.test_case_id || 0}, ${res.req_id || 0}, '${res.test_title.replace(/'/g, "\\'")}', '${(res.error_message || '').replace(/'/g, "\\'")}')">⚡ AI RCA</button>
                    ` : '<span style="color:#34d399;">✓ Clean</span>'}
                </td>
            `;
            this.resultsTbody.appendChild(tr);
        });
    }

    viewScreenshot(path, title) {
        const modal = document.getElementById('screenshot-modal');
        const modalTitle = document.getElementById('screenshot-modal-title');
        const modalBody = document.getElementById('screenshot-modal-body');

        modalTitle.textContent = `📸 Evidence Snapshot: ${title}`;
        modalBody.innerHTML = `<img src="${path}" style="width:100%;border-radius:8px;" onerror="this.src='/static/screenshots/fallback.svg'" />`;
        modal.style.display = 'flex';
    }

    async generateRCA(resultId, tcId, reqId, testTitle, errorMessage) {
        try {
            const res = await fetch('/api/generate-bug-report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    test_result_id: resultId,
                    test_case_id: tcId,
                    req_id: reqId,
                    test_title: testTitle,
                    error_message: errorMessage
                })
            });
            const data = await res.json();
            alert(`✅ AI Bug Report Generated!\nSeverity: ${data.bug_report.severity}\nRoot Cause: ${data.bug_report.root_cause_analysis}`);
            if (window.app) {
                window.app.navigateView('bugs-view');
            }
        } catch (err) {
            alert("Failed to generate AI RCA report.");
        }
    }
}

let testRunner;
document.addEventListener('DOMContentLoaded', () => {
    testRunner = new TestRunnerClient();
    window.runnerClient = testRunner;
});
