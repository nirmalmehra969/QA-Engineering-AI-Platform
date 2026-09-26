// SaaS - QA Engineering AI Platform Core Client
class QAApp {
    constructor() {
        this.currentView = 'dashboard-view';
        this.testCases = [];
        this.requirements = [];
        this.recentRuns = [];
        this.allRunsData = [];
        this.bugReports = [];
        this.datasets = {};
        this.selectedRunsForCompare = new Set();
        this.activeTestCase = null;
        this.metricExplanations = null;
        this.aiTelemetry = null;
        this.workflowGuidance = null;
        this.init();
    }

    init() {
        this.bindNavigation();
        this.bindRequirementStudio();
        this.bindDashboardScenarioSelector();
        this.bindCodeStudioTabs();
        this.bindMetricInfoModals();
        this.bindAiTrustModal();
        this.bindExecutionHistoryFiltersAndCompare();
        this.bindTestCaseApprovalWorkflow();
        this.bindDefectInspectionModals();
        this.loadDashboardData();
        this.loadTestData();
        this.loadCodeStudioContent('java-test');
        this.drawSparklines();
        this.checkAuthStatus();
        this.loadAiTelemetry();
    }

    bindNavigation() {
        document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetView = btn.getAttribute('data-view');
                this.navigateView(targetView);
            });
        });

        document.getElementById('btn-refresh-traceability')?.addEventListener('click', () => {
            this.loadTraceabilityMatrix();
        });

        document.getElementById('filter-traceability-status')?.addEventListener('change', () => {
            this.loadTraceabilityMatrix();
        });

        document.getElementById('filter-bug-severity')?.addEventListener('change', () => {
            this.renderBugReports();
        });

        document.getElementById('filter-bug-status')?.addEventListener('change', () => {
            this.renderBugReports();
        });

        document.getElementById('btn-view-matrix-shortcut')?.addEventListener('click', () => {
            this.navigateView('traceability-view');
        });

        document.getElementById('btn-next-action')?.addEventListener('click', () => {
            this.handleNextActionClick();
        });
    }

    navigateView(viewId) {
        document.querySelectorAll('.sidebar-nav .nav-item').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));

        const targetNav = document.querySelector(`.sidebar-nav .nav-item[data-view="${viewId}"]`);
        const targetSection = document.getElementById(viewId);

        if (targetNav) targetNav.classList.add('active');
        if (targetSection) targetSection.classList.add('active');

        const titleMap = {
            'dashboard-view': 'SaaS - QA Engineering AI Platform',
            'requirements-view': 'Requirements & AI Test Generation Studio',
            'traceability-view': 'End-to-End Requirement Traceability Matrix',
            'testcases-view': 'Test Suites & Gherkin Repository',
            'runner-view': 'Asynchronous Automation Runner',
            'bugs-view': 'Bug Reports & Root Cause Analysis (RCA)',
            'data-factory-view': 'Synthetic QA Test Data Factory',
            'code-studio-view': 'Java + Selenium + TestNG Code Studio',
            'settings-view': 'Platform, Security & AI Configuration'
        };
        const titleElem = document.getElementById('current-view-title');
        if (titleElem && titleMap[viewId]) {
            titleElem.textContent = titleMap[viewId];
        }

        if (viewId === 'traceability-view') this.loadTraceabilityMatrix();
        if (viewId === 'testcases-view') this.renderFullTestCasesList();
        if (viewId === 'bugs-view') this.renderBugReports();
        if (viewId === 'dashboard-view') this.loadDashboardData();
    }

    async checkAuthStatus() {
        try {
            const res = await fetch('/api/auth/me');
            const data = await res.json();
            const nameSpan = document.getElementById('header-user-name');
            if (data.authenticated && data.user) {
                nameSpan.textContent = `${data.user.full_name} (${data.user.role})`;
            } else {
                nameSpan.textContent = "Demo QA Tester";
            }
        } catch (e) {
            console.error("Auth check failed:", e);
        }
    }

    // =========================================================================
    // AI COPILOT TELEMETRY & TRUST MODAL
    // =========================================================================
    async loadAiTelemetry() {
        try {
            const res = await fetch('/api/ai/status');
            if (!res.ok) return;
            this.aiTelemetry = await res.json();
            this.renderAiStatusPill(this.aiTelemetry);
        } catch (err) {
            console.error("Failed to load AI telemetry:", err);
        }
    }

    renderAiStatusPill(telemetry) {
        const pill = document.getElementById('header-ai-status-pill');
        const label = document.getElementById('header-ai-provider-label');
        const tag = document.getElementById('header-ai-trust-tag');
        if (!pill || !label || !tag) return;

        label.textContent = telemetry.dashboard_label || 'Offline QA Heuristic Engine';
        tag.style.display = 'none'; // Trust tag is now merged into dashboard_label

        if (telemetry.is_fallback || telemetry.dashboard_label.startsWith("UNAVAILABLE")) {
            pill.className = 'ai-provider-pill badge-ai-fallback';
        } else {
            pill.className = 'ai-provider-pill badge-ai-online';
        }
    }

    bindAiTrustModal() {
        const pill = document.getElementById('header-ai-status-pill');
        const modal = document.getElementById('modal-ai-trust');
        const closeBtn = document.getElementById('close-ai-trust-btn');

        pill?.addEventListener('click', () => {
            this.openAiTrustModal();
        });

        closeBtn?.addEventListener('click', () => {
            if (modal) modal.style.display = 'none';
        });

        modal?.addEventListener('click', (e) => {
            if (e.target === modal) modal.style.display = 'none';
        });
    }

    async openAiTrustModal() {
        const modal = document.getElementById('modal-ai-trust');
        const body = document.getElementById('ai-trust-body');
        if (!modal || !body) return;

        // Fetch fresh telemetry from server
        try {
            const res = await fetch('/api/ai/status');
            if (res.ok) {
                this.aiTelemetry = await res.json();
            }
        } catch (e) {
            console.warn("Could not refresh AI telemetry:", e);
        }

        const tel = this.aiTelemetry || {
            active_provider: "Offline QA Heuristic Engine",
            trust_level: "Offline Heuristic (Zero External Transmission)",
            is_fallback: true,
            status: "OPERATIONAL",
            latency_display: "Not measured",
            model_name: "Heuristic BDD Rule-Engine v2.4",
            privacy_statement: "All test scenario synthesis and RCA diagnostics occur entirely locally in-memory. No data is sent to external third-party services.",
            capabilities: [
                { name: "BDD Scenario Generation (Gherkin)", status: "Implemented & Active", type: "Core" },
                { name: "Root Cause Analysis (RCA)", status: "Implemented & Active", type: "Core" },
                { name: "Requirement Impact Analysis", status: "Implemented & Active", type: "Core" },
                { name: "Traceability Matrix Mapping", status: "Implemented & Active", type: "Core" }
            ]
        };

        const statusLabel = tel.status || "OPERATIONAL";
        const latencyText = tel.latency_display || (tel.latency_ms ? `${tel.latency_ms} ms` : "Not measured");
        const trustBadgeColor = tel.is_fallback ? "#f59e0b" : "#10b981";
        const capabilitiesList = Array.isArray(tel.capabilities)
            ? tel.capabilities.map(c => {
                const name = typeof c === 'object' ? c.name : c;
                const status = typeof c === 'object' && c.status ? c.status : 'Implemented';
                return `<li style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid #1e293b;">
                    <span>${name}</span>
                    <span style="font-size:0.72rem;background:rgba(16,185,129,0.15);color:#34d399;padding:2px 8px;border-radius:4px;font-weight:600;">✓ ${status}</span>
                </li>`;
            }).join('')
            : '<li>Core QA Generation Active</li>';

        let lastGenHtml = '';
        if (tel.last_generation && tel.last_generation.provider_used) {
            const lg = tel.last_generation;
            const fallbackBadge = lg.is_fallback
                ? `<span style="font-size:0.75rem;background:rgba(245,158,11,0.2);color:#fbbf24;padding:2px 8px;border-radius:4px;font-weight:600;">Fallback Used</span>`
                : `<span style="font-size:0.75rem;background:rgba(16,185,129,0.2);color:#34d399;padding:2px 8px;border-radius:4px;font-weight:600;">Direct Generation</span>`;
            
            const reasonHtml = lg.fallback_reason ? `<div style="font-size:0.76rem;color:#fca5a5;margin-top:4px;">Reason: ${lg.fallback_reason}</div>` : '';

            lastGenHtml = `
                <div class="compare-card" style="margin-bottom:12px;background:#0d1424;border-color:#334155;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <h4 style="margin:0;">Last Generation Request</h4>
                        ${fallbackBadge}
                    </div>
                    <div style="font-size:0.8rem;color:#cbd5e1;margin-top:6px;">
                        Provider: <code style="color:var(--neon-cyan);">${lg.provider_used}</code>
                        ${lg.latency_ms ? ` • Duration: <code>${lg.latency_ms} ms</code>` : ''}
                    </div>
                    ${reasonHtml}
                </div>
            `;
        }

        body.innerHTML = `
            <div class="compare-card" style="margin-bottom:14px;border-left:4px solid var(--neon-cyan);">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <h4 style="margin:0;color:#f8fafc;font-size:1.05rem;">${tel.dashboard_label || 'Offline QA Heuristic Engine'}</h4>
                        <span style="font-size:0.75rem;color:#94a3b8;">Engine Code: <code>${tel.model_name || tel.provider_code || 'Heuristic BDD Rule-Engine v2.4'}</code></span>
                    </div>
                    <span class="badge-status ${statusLabel === 'OPERATIONAL' ? 'passed' : 'running'}">${statusLabel}</span>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
                <div class="compare-card">
                    <h4>Trust Mode</h4>
                    <span style="color:${trustBadgeColor};font-weight:700;font-size:0.95rem;display:block;margin-top:4px;">${tel.trust_level || 'Verified Offline'}</span>
                </div>
                <div class="compare-card">
                    <h4>Average Response Latency</h4>
                    <span style="color:var(--neon-cyan);font-weight:700;font-size:0.95rem;display:block;margin-top:4px;">${latencyText}</span>
                </div>
            </div>

            ${lastGenHtml}

            <div class="defect-rca-box" style="margin-bottom:14px;background:rgba(15,23,42,0.85);border-color:#334155;">
                <strong style="color:#38bdf8;font-size:0.85rem;">🛡️ Privacy & Data Transmission Policy:</strong>
                <p style="margin-top:6px;font-size:0.8rem;color:#cbd5e1;line-height:1.45;">
                    ${tel.privacy_statement || 'All generation operates locally in-memory using deterministic rule templates. No test requirements or project data are transmitted to external servers.'}
                </p>
            </div>

            <div class="compare-card">
                <h4 style="margin-bottom:8px;">Verified Platform Capabilities</h4>
                <ul style="margin:0;padding:0;list-style:none;font-size:0.82rem;color:#e2e8f0;">
                    ${capabilitiesList}
                </ul>
            </div>
        `;

        modal.style.display = 'flex';
    }

    // =========================================================================
    // METRIC CALCULATION TRANSPARENCY MODAL
    // =========================================================================
    bindMetricInfoModals() {
        const modal = document.getElementById('modal-metric-info');
        const closeBtn = document.getElementById('close-metric-info-btn');

        document.querySelectorAll('.btn-info-metric').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const key = btn.getAttribute('data-metric');
                this.openMetricInfoModal(key);
            });
        });

        closeBtn?.addEventListener('click', () => {
            if (modal) modal.style.display = 'none';
        });

        modal?.addEventListener('click', (e) => {
            if (e.target === modal) modal.style.display = 'none';
        });
    }

    openMetricInfoModal(metricKey) {
        const modal = document.getElementById('modal-metric-info');
        const titleElem = document.getElementById('metric-info-title');
        const bodyElem = document.getElementById('metric-info-body');
        if (!modal || !bodyElem) return;

        const metaMap = {
            'success_rate': {
                title: "Test Success Rate Calculation",
                icon: "📈",
                formula: "(Total Passed Tests across All Runs / Total Executed Tests) × 100",
                period: "Lifetime aggregate across all completed background test runs",
                source: "Database table: test_runs & test_results",
                note: "Unexecuted draft test cases and queued runs are excluded. This reflects live execution pass stability."
            },
            'requirement_coverage': {
                title: "Requirement Coverage Scope",
                icon: "🎯",
                formula: "(Requirements with ≥ 1 Approved Test Case / Total Active Requirements) × 100",
                period: "Current repository scope (Active Software Requirements)",
                source: "Database tables: requirements & test_cases",
                note: "⚠️ Functional User Story Traceability: This measures requirement acceptance coverage, NOT bytecode or branch code coverage (e.g. JaCoCo). A requirement is marked COVERED once at least one test case is reviewed and APPROVED."
            },
            'test_cases': {
                title: "Total Test Cases & Lifecycle State",
                icon: "📋",
                formula: "Count of all generated, reviewed, and approved Gherkin scenarios",
                period: "Active repository test catalog",
                source: "Database table: test_cases (group by status: APPROVED, IN_REVIEW, DRAFT, REJECTED)",
                note: "Only test cases in APPROVED status are included when executing the Full Regression Suite in Selenium."
            },
            'active_bugs': {
                title: "Active Bugs & Assertion Failures",
                icon: "🐞",
                formula: "Count of unresolved test assertion failures and runtime exceptions",
                period: "Latest execution runs with failed assertions",
                source: "Database tables: bug_reports and failed test_results",
                note: "Each active bug record contains the complete failure exception message, stack trace, screenshot evidence, and AI Root Cause Analysis (RCA)."
            }
        };

        const item = metaMap[metricKey] || metaMap['success_rate'];
        if (titleElem) titleElem.textContent = `${item.icon} ${item.title}`;

        bodyElem.innerHTML = `
            <div class="compare-card" style="margin-bottom:12px;">
                <h4>Mathematical Formula</h4>
                <div style="background:#020617;border:1px solid #1e293b;padding:8px 12px;border-radius:6px;font-family:var(--font-code);color:var(--neon-cyan);font-size:0.85rem;">
                    ${item.formula}
                </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
                <div class="compare-card">
                    <h4>Measurement Period</h4>
                    <span style="font-size:0.82rem;color:#cbd5e1;">${item.period}</span>
                </div>
                <div class="compare-card">
                    <h4>Primary Data Source</h4>
                    <span style="font-size:0.82rem;color:#cbd5e1;">${item.source}</span>
                </div>
            </div>

            <div class="defect-rca-box">
                <strong style="color:#fbbf24;">ℹ️ QA Engineering Note:</strong>
                <p style="margin-top:6px;font-size:0.8rem;color:#cbd5e1;line-height:1.4;">
                    ${item.note}
                </p>
            </div>
        `;

        modal.style.display = 'flex';
    }

    // =========================================================================
    // DASHBOARD DATA LOADER & BINDING
    // =========================================================================
    async loadDashboardData() {
        try {
            const res = await fetch('/api/dashboard/stats');
            if (!res.ok) return;
            const data = await res.json();

            // 1. Metrics & KPI Cards
            document.getElementById('kpi-success-rate').textContent = `${data.success_rate}%`;
            
            const passed = (data.total_passed_tests !== undefined && data.total_passed_tests !== null) ? data.total_passed_tests : (data.total_passed ?? 0);
            const totalExec = (data.total_executed_tests !== undefined && data.total_executed_tests !== null) ? data.total_executed_tests : (data.total_executed ?? 0);
            const calcTextElem = document.getElementById('kpi-success-calc-text');
            if (calcTextElem) {
                if (typeof totalExec === 'number' && totalExec > 0) {
                    calcTextElem.textContent = `Lifetime: ${passed}/${totalExec} assertions passed`;
                } else {
                    calcTextElem.textContent = "No assertion data available";
                }
            }

            document.getElementById('kpi-code-coverage').textContent = `${data.code_coverage}%`;
            const rawCov = data.coverage_counts || {};
            const covCounts = {
                covered: rawCov.covered || 0,
                partial: rawCov.partially_covered ?? rawCov.partial ?? 0,
                uncovered: rawCov.uncovered || 0,
                total: rawCov.total || 0
            };
            document.getElementById('kpi-coverage-calc-text').textContent = `${covCounts.covered} of ${covCounts.total} User Stories Covered (Functional)`;

            document.getElementById('kpi-total-tests').textContent = data.total_test_cases;
            document.getElementById('kpi-approved-pill').textContent = `✓ ${data.approved_test_cases || 0} Approved`;
            document.getElementById('pill-draft-count').textContent = `${data.draft_test_cases || 0} Draft`;
            const reviewCountElem = document.getElementById('pill-review-count');
            if (reviewCountElem) {
                reviewCountElem.textContent = `${data.in_review_test_cases || 0} In Review`;
            }

            document.getElementById('kpi-active-bugs').textContent = data.active_bugs;
            const bugsSub = document.getElementById('kpi-bugs-subtext');
            if (bugsSub) {
                bugsSub.textContent = data.active_bugs > 0 ? "Click to inspect failure logs & RCA" : "Zero regressions detected";
            }

            this.testCases = data.test_cases || [];
            this.requirementCoverageList = data.requirement_coverage_list || [];
            this.allRunsData = data.recent_runs || [];
            this.recentRuns = this.allRunsData;
            this.bugReports = data.bug_reports || [];
            this.metricExplanations = data.metric_explanations || null;
            this.workflowGuidance = data.workflow_guidance || null;

            // 2. Workflow Guidance & Next Action
            this.updateWorkflowAndNextAction(this.workflowGuidance);

            // 3. Requirement Coverage Widget
            this.renderRequirementCoverageWidget(data.requirement_coverage_list || [], covCounts, data.code_coverage);

            // 4. Latest Regression Alert Banner
            this.renderRegressionAlertBanner(data.regression_info);

            // 5. Execution History Table & Filters
            this.applyHistoryFilters();

            // 6. Test Case Scenario Selector
            this.populateScenarioSelector(this.testCases);

            this.drawSparklines();
        } catch (err) {
            console.error("Failed to load dashboard metrics:", err);
        }
    }

    // =========================================================================
    // WORKFLOW GUIDANCE & CONTEXTUAL NEXT ACTION
    // =========================================================================
    updateWorkflowAndNextAction(guidance) {
        if (!guidance) return;

        // Reset step highlights
        const steps = ['req', 'gen', 'approve', 'exec', 'triage'];
        steps.forEach(s => {
            document.getElementById(`step-${s}`)?.classList.remove('active-step');
        });

        // Highlight current step
        const activeElem = document.getElementById(`step-${guidance.active_step}`);
        if (activeElem) activeElem.classList.add('active-step');

        // Update Next Action Banner
        const stageTitle = document.getElementById('next-action-stage-title');
        const descElem = document.getElementById('next-action-desc');
        const btnElem = document.getElementById('btn-next-action');

        if (stageTitle) stageTitle.textContent = guidance.stage_title || 'Current Stage: Automation Readiness';
        if (descElem) descElem.textContent = guidance.description || 'Proceed with next QA lifecycle action.';
        if (btnElem) {
            btnElem.textContent = guidance.action_label || 'Execute Suite';
            btnElem.setAttribute('data-target', guidance.action_target || 'runner-view');
        }
    }

    handleNextActionClick() {
        const btn = document.getElementById('btn-next-action');
        const target = btn?.getAttribute('data-target') || 'runner-view';

        if (target.startsWith('view:')) {
            const view = target.replace('view:', '');
            this.navigateView(view);
        } else if (target === 'runner-view') {
            this.navigateView('runner-view');
        } else if (target === 'requirements-view') {
            this.navigateView('requirements-view');
        } else if (target === 'testcases-view') {
            this.navigateView('testcases-view');
        } else if (target === 'bugs-view') {
            this.navigateView('bugs-view');
        } else if (target === 'approve-scenario') {
            if (this.activeTestCase) {
                this.openTcApprovalModal(this.activeTestCase.id);
            } else {
                this.navigateView('testcases-view');
            }
        } else {
            this.navigateView('runner-view');
        }
    }

    // =========================================================================
    // REQUIREMENT TRACEABILITY & COVERAGE WIDGET
    // =========================================================================
    renderRequirementCoverageWidget(reqList, counts, percentage) {
        const summaryBadge = document.getElementById('req-cov-summary-badge');
        if (summaryBadge) {
            summaryBadge.textContent = `${percentage}% Traced (${counts.covered}/${counts.total} Covered)`;
        }

        const barCovered = document.getElementById('req-cov-bar-covered');
        const barPartial = document.getElementById('req-cov-bar-partial');
        const barUncovered = document.getElementById('req-cov-bar-uncovered');

        const total = counts.total || 1;
        const coveredVal = counts.covered || 0;
        const partialVal = counts.partially_covered ?? counts.partial ?? 0;
        const uncoveredVal = counts.uncovered || 0;
        const coveredPct = Math.round((coveredVal / total) * 100);
        const partialPct = Math.round((partialVal / total) * 100);
        const uncoveredPct = Math.max(0, 100 - coveredPct - partialPct);

        if (barCovered) barCovered.style.width = `${coveredPct}%`;
        if (barPartial) barPartial.style.width = `${partialPct}%`;
        if (barUncovered) barUncovered.style.width = `${uncoveredPct}%`;

        const legendCovered = document.getElementById('legend-covered-count');
        const legendPartial = document.getElementById('legend-partial-count');
        const legendUncovered = document.getElementById('legend-uncovered-count');
        if (legendCovered) legendCovered.textContent = coveredVal;
        if (legendPartial) legendPartial.textContent = partialVal;
        if (legendUncovered) legendUncovered.textContent = uncoveredVal;

        const grid = document.getElementById('dashboard-req-cov-list');
        if (!grid) return;
        grid.innerHTML = '';

        if (reqList.length === 0) {
            grid.innerHTML = '<div style="color:#94a3b8;font-size:0.8rem;padding:10px;">No requirements mapped.</div>';
            return;
        }

        reqList.forEach(r => {
            const card = document.createElement('div');
            card.className = 'req-cov-item-card';
            
            const statusVal = (r.coverage_status || r.status || 'UNCOVERED').toUpperCase();
            const statusClass = statusVal === 'COVERED' ? 'badge-approved' : (statusVal === 'PARTIALLY_COVERED' || statusVal === 'PARTIAL' ? 'badge-review' : 'badge-rejected');
            const moduleName = r.module_name || r.module || 'General';
            const approvedCount = r.approved_test_cases ?? r.approved_count ?? 0;
            const totalCount = r.total_test_cases ?? r.test_count ?? 0;

            card.innerHTML = `
                <div class="req-cov-item-top">
                    <span class="req-cov-module-badge">${moduleName}</span>
                    <span class="badge-status ${statusClass}">${statusVal}</span>
                </div>
                <div class="req-cov-item-title">#REQ-${r.id}: ${r.title}</div>
                <div class="req-cov-item-bottom">
                    <span>${approvedCount}/${totalCount} Tests Approved</span>
                    <button class="btn-xs btn-outline" onclick="app.navigateView('requirements-view')">Manage</button>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    // =========================================================================
    // REGRESSION ALERT BANNER
    // =========================================================================
    renderRegressionAlertBanner(regInfo) {
        const banner = document.getElementById('dashboard-regression-banner');
        const icon = document.getElementById('regression-banner-icon');
        const title = document.getElementById('regression-banner-title');
        const desc = document.getElementById('regression-banner-desc');
        if (!banner || !title || !desc) return;

        if (regInfo && regInfo.has_regressions) {
            banner.className = 'regression-alert-banner has-regressions';
            if (icon) icon.textContent = '🚨';
            title.textContent = `Regression Alert: ${regInfo.regression_count} Test(s) Failing in Run #${regInfo.run_id}`;
            desc.textContent = `Latest automated regression detected assertion failures in ${regInfo.suite_name || 'suite'}. Review failure stack traces and open defects.`;
        } else {
            banner.className = 'regression-alert-banner';
            if (icon) icon.textContent = '🛡️';
            title.textContent = "Clean Regression Result: All Automated Assertions Verified";
            desc.textContent = "The most recent test execution completed without regressions. Zero blocking defects detected.";
        }
    }

    // =========================================================================
    // EXECUTION HISTORY: FILTERING, SEARCH, SORT & COMPARE
    // =========================================================================
    bindExecutionHistoryFiltersAndCompare() {
        const statusFilter = document.getElementById('history-filter-status');
        const modeFilter = document.getElementById('history-filter-mode');
        const searchInput = document.getElementById('history-search-input');
        const sortSelect = document.getElementById('history-sort-select');
        const compareBtn = document.getElementById('btn-compare-runs');
        const compareModal = document.getElementById('modal-run-comparison');
        const closeCompareBtn = document.getElementById('close-compare-modal-btn');

        statusFilter?.addEventListener('change', () => this.applyHistoryFilters());
        modeFilter?.addEventListener('change', () => this.applyHistoryFilters());
        searchInput?.addEventListener('input', () => this.applyHistoryFilters());
        sortSelect?.addEventListener('change', () => this.applyHistoryFilters());

        compareBtn?.addEventListener('click', () => {
            this.openRunComparisonModal();
        });

        closeCompareBtn?.addEventListener('click', () => {
            if (compareModal) compareModal.style.display = 'none';
        });

        compareModal?.addEventListener('click', (e) => {
            if (e.target === compareModal) compareModal.style.display = 'none';
        });
    }

    applyHistoryFilters() {
        const status = document.getElementById('history-filter-status')?.value || 'ALL';
        const mode = document.getElementById('history-filter-mode')?.value || 'ALL';
        const search = document.getElementById('history-search-input')?.value.toLowerCase().trim() || '';
        const sortBy = document.getElementById('history-sort-select')?.value || 'newest';

        let filtered = [...this.allRunsData];

        // Filter by Status
        if (status === 'PASSED') {
            filtered = filtered.filter(r => r.status === 'COMPLETED' && r.failed_tests === 0);
        } else if (status === 'DEFECTS') {
            filtered = filtered.filter(r => r.failed_tests > 0);
        } else if (status === 'QUEUED') {
            filtered = filtered.filter(r => r.status === 'QUEUED' || r.status === 'RUNNING');
        }

        // Filter by Execution Mode
        if (mode === 'SELENIUM') {
            filtered = filtered.filter(r => (r.execution_mode || '').toLowerCase().includes('selenium'));
        } else if (mode === 'SIMULATED') {
            filtered = filtered.filter(r => !(r.execution_mode || '').toLowerCase().includes('selenium'));
        }

        // Search Filter
        if (search) {
            filtered = filtered.filter(r => {
                const idStr = `run-${r.id}`.toLowerCase();
                const suiteStr = (r.suite_name || '').toLowerCase();
                return idStr.includes(search) || suiteStr.includes(search);
            });
        }

        // Sort
        if (sortBy === 'newest') {
            filtered.sort((a, b) => b.id - a.id);
        } else if (sortBy === 'oldest') {
            filtered.sort((a, b) => a.id - b.id);
        } else if (sortBy === 'pass_rate_desc') {
            filtered.sort((a, b) => {
                const rateA = a.total_tests > 0 ? (a.passed_tests / a.total_tests) : 0;
                const rateB = b.total_tests > 0 ? (b.passed_tests / b.total_tests) : 0;
                return rateB - rateA;
            });
        } else if (sortBy === 'duration_asc') {
            filtered.sort((a, b) => (a.duration_sec || 0) - (b.duration_sec || 0));
        }

        this.renderRecentRunsTable(filtered);
    }

    renderRecentRunsTable(runs) {
        const tbody = document.getElementById('recent-runs-tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (runs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="11" style="text-align:center;color:#94a3b8;padding:24px;">No execution history matching filter criteria.</td></tr>`;
            return;
        }

        runs.forEach(r => {
            const tr = document.createElement('tr');
            const isChecked = this.selectedRunsForCompare.has(r.id);

            const isSelenium = (r.execution_mode || '').toLowerCase().includes('selenium');
            const engineBadge = isSelenium
                ? `<span class="badge-tag" style="background:#0f172a;color:#00e5ff;border:1px solid rgba(0,229,255,0.3);" title="Real Selenium WebDriver (Chrome Headless v124)">Selenium · Headless</span>`
                : `<span class="badge-tag" style="background:#0f172a;color:#a855f7;border:1px solid rgba(168,85,247,0.3);" title="In-Memory Fast Engine">Simulated</span>`;

            const failedBadge = r.failed_tests > 0
                ? `<span class="failure-count-badge" title="Click to inspect failure stack trace & RCA" onclick="app.openDefectModal(${r.id})">${r.failed_tests} 🐞</span>`
                : `<span style="color:#94a3b8;">0</span>`;

            const jobStatus = r.status || 'COMPLETED';
            const jobStatusClass = jobStatus === 'COMPLETED' ? 'badge-completed' : (jobStatus === 'RUNNING' ? 'badge-running' : 'badge-draft');

            let outcomeText = 'PASSED';
            let outcomeClass = 'passed';
            if (r.failed_tests > 0 && r.passed_tests > 0) {
                outcomeText = 'PARTIAL';
                outcomeClass = 'badge-review';
            } else if (r.failed_tests > 0 && r.passed_tests === 0) {
                outcomeText = 'FAILED';
                outcomeClass = 'failed';
            } else if (r.total_tests === 0) {
                outcomeText = 'NO_TESTS';
                outcomeClass = 'badge-draft';
            }

            tr.innerHTML = `
                <td style="text-align:center;">
                    <input type="checkbox" class="run-select-checkbox" data-run-id="${r.id}" ${isChecked ? 'checked' : ''} />
                </td>
                <td><code>#RUN-${r.id}</code></td>
                <td style="white-space:nowrap;"><strong>${r.suite_name || 'Full Regression'}</strong></td>
                <td>${engineBadge}</td>
                <td>${r.total_tests}</td>
                <td><span style="color:#34d399;font-weight:bold;">${r.passed_tests}</span></td>
                <td>${failedBadge}</td>
                <td>${r.duration_sec || 0}s</td>
                <td><span class="badge-status ${jobStatusClass}">${jobStatus}</span></td>
                <td><span class="badge-status ${outcomeClass}">${outcomeText}</span></td>
                <td style="white-space:nowrap;">
                    <div style="display:flex;gap:6px;">
                        <button class="btn-xs btn-outline" onclick="app.viewRunDetails(${r.id})">Logs</button>
                        ${r.failed_tests > 0 ? `<button class="btn-xs btn-danger-outline" onclick="app.openDefectModal(${r.id})">Defects</button>` : ''}
                    </div>
                </td>
            `;

            // Bind checkbox
            const chk = tr.querySelector('.run-select-checkbox');
            chk?.addEventListener('change', (e) => {
                this.handleRunSelection(r.id, e.target.checked);
            });

            tbody.appendChild(tr);
        });

        this.updateCompareButtonState();
    }

    handleRunSelection(runId, isSelected) {
        if (isSelected) {
            if (this.selectedRunsForCompare.size >= 2) {
                alert("You can compare a maximum of 2 runs side-by-side. Uncheck one first.");
                this.applyHistoryFilters();
                return;
            }
            this.selectedRunsForCompare.add(runId);
        } else {
            this.selectedRunsForCompare.delete(runId);
        }
        this.updateCompareButtonState();
    }

    updateCompareButtonState() {
        const btn = document.getElementById('btn-compare-runs');
        if (!btn) return;
        const count = this.selectedRunsForCompare.size;

        if (count === 2) {
            btn.disabled = false;
            btn.textContent = `⚖️ Compare Runs (2/2 Selected)`;
            btn.classList.remove('btn-outline');
            btn.classList.add('btn-cyan');
        } else {
            btn.disabled = true;
            btn.textContent = `⚖️ Compare Runs (${count}/2 Selected)`;
            btn.classList.remove('btn-cyan');
            btn.classList.add('btn-outline');
        }
    }

    async openRunComparisonModal() {
        if (this.selectedRunsForCompare.size !== 2) return;
        const [runAId, runBId] = Array.from(this.selectedRunsForCompare);

        const modal = document.getElementById('modal-run-comparison');
        const body = document.getElementById('compare-modal-body');
        if (!modal || !body) return;

        body.innerHTML = '<div style="text-align:center;padding:30px;color:#94a3b8;">Computing side-by-side delta & diff analysis...</div>';
        modal.style.display = 'flex';

        try {
            const res = await fetch(`/api/test-runs/compare?run_a=${runAId}&run_b=${runBId}`);
            if (!res.ok) {
                body.innerHTML = '<div style="color:#ef4444;padding:20px;">Failed to compare selected runs.</div>';
                return;
            }
            const data = await res.json();
            this.renderComparisonContent(data);
        } catch (err) {
            console.error("Comparison error:", err);
            body.innerHTML = `<div style="color:#ef4444;padding:20px;">Error loading comparison: ${err}</div>`;
        }
    }

    renderComparisonContent(data) {
        const body = document.getElementById('compare-modal-body');
        if (!body) return;

        const a = data.run_a;
        const b = data.run_b;
        const d = data.deltas;

        const passDeltaSign = d.pass_rate_diff >= 0 ? `+${d.pass_rate_diff}%` : `${d.pass_rate_diff}%`;
        const passDeltaClass = d.pass_rate_diff > 0 ? 'delta-pos' : (d.pass_rate_diff < 0 ? 'delta-neg' : 'delta-neutral');

        const durDeltaSign = d.duration_diff_sec >= 0 ? `+${d.duration_diff_sec}s` : `${d.duration_diff_sec}s`;

        body.innerHTML = `
            <div class="compare-summary-cards">
                <div class="compare-card">
                    <h4>Run A (#${a.id})</h4>
                    <div class="compare-card-val">${a.passed_tests}/${a.total_tests} Pass</div>
                    <span style="font-size:0.75rem;color:#94a3b8;">${a.execution_mode} • ${a.duration_sec}s</span>
                </div>
                <div class="compare-card">
                    <h4>Run B (#${b.id})</h4>
                    <div class="compare-card-val">${b.passed_tests}/${b.total_tests} Pass</div>
                    <span style="font-size:0.75rem;color:#94a3b8;">${b.execution_mode} • ${b.duration_sec}s</span>
                </div>
                <div class="compare-card">
                    <h4>Pass Rate Delta</h4>
                    <div class="compare-card-val">${a.pass_rate}% → ${b.pass_rate}% <span class="delta-badge ${passDeltaClass}">${passDeltaSign}</span></div>
                    <span style="font-size:0.75rem;color:#94a3b8;">Duration Delta: ${durDeltaSign}</span>
                </div>
                <div class="compare-card">
                    <h4>Regression Status</h4>
                    <div class="compare-card-val" style="color:${d.regressions_count > 0 ? '#f87171' : '#34d399'};">
                        ${d.regressions_count} Regressions • ${d.fixes_count} Fixes
                    </div>
                    <span style="font-size:0.75rem;color:#94a3b8;">${d.regressions_count === 0 ? 'Clean comparison' : 'Attention required'}</span>
                </div>
            </div>

            <h4 style="margin:16px 0 8px 0;font-size:0.92rem;color:#f8fafc;">Test-by-Test Execution Diff</h4>
            <div class="table-responsive">
                <table class="saas-table diff-table">
                    <thead>
                        <tr>
                            <th>Test Title</th>
                            <th>Run #${a.id} Result</th>
                            <th>Run #${b.id} Result</th>
                            <th>Duration Δ</th>
                            <th>Delta Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(data.test_diffs || []).map(t => {
                            const badge = t.delta_status === 'REGRESSION'
                                ? '<span class="diff-badge-regression">REGRESSION 🚨</span>'
                                : (t.delta_status === 'FIXED'
                                    ? '<span class="diff-badge-fixed">FIXED ✓</span>'
                                    : '<span class="diff-badge-unchanged">UNCHANGED</span>');

                            return `
                                <tr>
                                    <td><strong>${t.title}</strong></td>
                                    <td><span class="badge-status ${t.status_a === 'PASSED' ? 'passed' : 'failed'}">${t.status_a}</span></td>
                                    <td><span class="badge-status ${t.status_b === 'PASSED' ? 'passed' : 'failed'}">${t.status_b}</span></td>
                                    <td><code>${t.duration_diff_sec >= 0 ? '+' : ''}${t.duration_diff_sec}s</code></td>
                                    <td>${badge}</td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    // =========================================================================
    // DEFECT INSPECTION & FAILURE EVIDENCE MODAL
    // =========================================================================
    bindDefectInspectionModals() {
        const modal = document.getElementById('modal-defect-details');
        const closeBtn = document.getElementById('close-defect-modal-btn');
        const kpiBugCard = document.getElementById('kpi-card-bugs');
        const kpiDefectCard = document.getElementById('kpi-card-defects');

        const openHandler = () => this.openDefectModal();
        kpiBugCard?.addEventListener('click', openHandler);
        kpiDefectCard?.addEventListener('click', openHandler);

        closeBtn?.addEventListener('click', () => {
            if (modal) modal.style.display = 'none';
        });

        modal?.addEventListener('click', (e) => {
            if (e.target === modal) modal.style.display = 'none';
        });
    }

    async openDefectModal(runId = null) {
        const modal = document.getElementById('modal-defect-details');
        const titleElem = document.getElementById('defect-modal-title');
        const subElem = document.getElementById('defect-modal-subtitle');
        const bodyElem = document.getElementById('defect-modal-body');
        if (!modal || !bodyElem) return;

        if (titleElem) {
            titleElem.textContent = runId ? `🐞 Defect Details & Failure Evidence (Run #${runId})` : `🐞 Active Bugs & Failure Evidence Repository`;
        }
        if (subElem) {
            subElem.textContent = "Live stack traces, element locator mismatches, failure screenshots and AI RCA";
        }

        bodyElem.innerHTML = '<div style="text-align:center;padding:30px;color:#94a3b8;">Loading defect stack traces & evidence...</div>';
        modal.style.display = 'flex';

        try {
            const url = runId ? `/api/defects/details?run_id=${runId}` : `/api/defects/details`;
            const res = await fetch(url);
            const data = await res.json();
            this.renderDefectModalContent(data.defects || []);
        } catch (err) {
            console.error("Defect details error:", err);
            bodyElem.innerHTML = `<div style="color:#ef4444;padding:20px;">Failed to load defect details: ${err}</div>`;
        }
    }

    renderDefectModalContent(defects) {
        const bodyElem = document.getElementById('defect-modal-body');
        if (!bodyElem) return;

        if (defects.length === 0) {
            bodyElem.innerHTML = `
                <div class="empty-state-card" style="padding:40px;">
                    <span class="empty-icon">🎉</span>
                    <h4>No Active Defects Found</h4>
                    <p>All test assertions passed successfully. Zero active bugs recorded.</p>
                </div>
            `;
            return;
        }

        bodyElem.innerHTML = defects.map(d => `
            <div class="defect-card">
                <div class="defect-header">
                    <div class="defect-title">${d.title}</div>
                    <div>
                        <span class="badge-status failed">${d.severity || 'CRITICAL'}</span>
                        <span class="badge-tag">${d.module}</span>
                    </div>
                </div>
                <div class="defect-meta">
                    Reported: <strong>${d.created_at || 'Recent'}</strong> • Test ID: <code>#TC-${d.test_case_id || 'N/A'}</code>
                </div>
                
                <div style="margin-bottom:6px;font-weight:600;font-size:0.8rem;color:#fca5a5;">Failure Assertion Error & Stack Trace:</div>
                <div class="defect-error-box">${d.error_message || 'AssertionError: Expected element was not found on DOM'}</div>

                <div class="defect-rca-box">
                    <strong style="color:#c084fc;">🤖 AI Root Cause Analysis (RCA):</strong>
                    <p style="margin:4px 0 0 0;">${d.root_cause_analysis || 'Under investigation'}</p>
                </div>

                <div class="defect-fix-box">
                    <strong style="color:#34d399;">💡 Suggested Fix:</strong>
                    <p style="margin:4px 0 0 0;font-family:var(--font-code);">${d.ai_fix_suggestion || 'Review element locators'}</p>
                </div>

                ${d.screenshot_path ? `
                    <div style="margin-top:10px;">
                        <span style="font-size:0.75rem;color:#94a3b8;display:block;margin-bottom:4px;">📸 Failure Evidence Screenshot:</span>
                        <img src="${d.screenshot_path}" class="defect-screenshot-thumb" onclick="app.showFullScreenshot('${d.screenshot_path}')" />
                    </div>
                ` : ''}

                <div style="margin-top:12px;display:flex;justify-content:flex-end;gap:8px;">
                    <button class="btn-xs btn-outline" onclick="app.copyJiraBugMarkdown(${JSON.stringify(d).replace(/"/g, '&quot;')})">Copy Jira Issue Markdown</button>
                </div>
            </div>
        `).join('');
    }

    showFullScreenshot(path) {
        const modal = document.getElementById('screenshot-modal');
        const body = document.getElementById('screenshot-modal-body');
        if (!modal || !body) return;
        body.innerHTML = `<img src="${path}" style="max-width:100%;border-radius:8px;" />`;
        modal.style.display = 'flex';
    }

    // =========================================================================
    // TEST CASE APPROVAL & LIFECYCLE WORKFLOW
    // =========================================================================
    bindDashboardScenarioSelector() {
        const selector = document.getElementById('dashboard-scenario-selector');
        const runBtn = document.getElementById('btn-quick-run-scenario');
        const approveBtn = document.getElementById('btn-quick-approve-scenario');
        const reviewBtn = document.getElementById('btn-quick-review-scenario');
        const rejectBtn = document.getElementById('btn-quick-reject-scenario');

        selector?.addEventListener('change', () => {
            const tcId = parseInt(selector.value, 10);
            const found = this.testCases.find(t => t.id === tcId);
            if (found) {
                this.displayActiveTestCase(found);
            }
        });

        runBtn?.addEventListener('click', () => {
            if (this.activeTestCase) {
                const status = (this.activeTestCase.status || 'DRAFT').toUpperCase();
                if (status !== 'APPROVED') {
                    alert(`⚠️ QA Approval Rule Violation: Scenario #${this.activeTestCase.id} is currently in [${status}] status.\n\nOnly APPROVED test cases are eligible for automated execution. Please review and click '✓ Approve' first.`);
                    return;
                }
            }
            this.navigateView('runner-view');
            document.getElementById('btn-start-automation')?.click();
        });

        approveBtn?.addEventListener('click', () => {
            if (this.activeTestCase) {
                this.updateTestCaseStatusQuick(this.activeTestCase.id, 'APPROVED');
            }
        });

        reviewBtn?.addEventListener('click', () => {
            if (this.activeTestCase) {
                this.updateTestCaseStatusQuick(this.activeTestCase.id, 'IN_REVIEW');
            }
        });

        rejectBtn?.addEventListener('click', () => {
            if (this.activeTestCase) {
                this.openTcApprovalModal(this.activeTestCase.id, 'REJECTED');
            }
        });
    }

    populateScenarioSelector(cases) {
        const selector = document.getElementById('dashboard-scenario-selector');
        if (!selector) return;
        selector.innerHTML = '';

        if (!cases || cases.length === 0) {
            selector.innerHTML = '<option value="">No test cases available</option>';
            return;
        }

        cases.forEach(tc => {
            const opt = document.createElement('option');
            opt.value = tc.id;
            opt.textContent = `[${tc.status || 'DRAFT'}] #TC-${tc.id}: ${tc.title}`;
            selector.appendChild(opt);
        });

        if (cases.length > 0) {
            selector.value = cases[0].id;
            this.displayActiveTestCase(cases[0]);
        }
    }

    displayActiveTestCase(tc) {
        this.activeTestCase = tc;
        const display = document.getElementById('dashboard-gherkin-display');
        const statusBadge = document.getElementById('scenario-status-badge');
        const reviewerInfo = document.getElementById('scenario-reviewer-info');
        const dateSpan = document.getElementById('scenario-reviewed-at');
        const linkedReq = document.getElementById('scenario-linked-req');
        const alertBanner = document.getElementById('dashboard-re-review-alert');

        if (display) display.textContent = tc.gherkin_text || 'No Gherkin Defined';

        const st = (tc.status || 'DRAFT').toUpperCase();
        if (statusBadge) {
            statusBadge.textContent = st;
            statusBadge.className = `badge-status badge-${st.toLowerCase()}`;
        }

        if (reviewerInfo) {
            reviewerInfo.innerHTML = `Reviewer: <strong>${tc.reviewer || 'Not reviewed yet'}</strong>`;
        }
        if (dateSpan) {
            dateSpan.innerHTML = `Timestamp: <strong>${tc.reviewed_at ? tc.reviewed_at.split(' ')[0] : 'Pending sign-off'}</strong>`;
        }
        if (linkedReq) {
            let reqTitle = tc.requirement_title;
            if (!reqTitle && tc.req_id && this.requirementCoverageList) {
                const foundReq = this.requirementCoverageList.find(r => r.id === tc.req_id);
                if (foundReq) reqTitle = foundReq.title;
            }
            if (tc.req_id) {
                linkedReq.innerHTML = `Linked Story: <strong>#REQ-${tc.req_id}: ${reqTitle || 'Requirement #' + tc.req_id}</strong>`;
            } else {
                linkedReq.innerHTML = `Linked Story: <strong>Unlinked / General Story</strong>`;
            }
        }

        if (alertBanner) {
            alertBanner.style.display = (tc.needs_review === 1) ? 'block' : 'none';
        }
    }

    bindTestCaseApprovalWorkflow() {
        const modal = document.getElementById('modal-tc-approval');
        const form = document.getElementById('tc-approval-form');
        const closeBtn = document.getElementById('close-tc-approval-btn');
        const cancelBtn = document.getElementById('cancel-tc-approval-btn');

        closeBtn?.addEventListener('click', () => {
            if (modal) modal.style.display = 'none';
        });

        cancelBtn?.addEventListener('click', () => {
            if (modal) modal.style.display = 'none';
        });

        form?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const tcId = document.getElementById('approval-tc-id')?.value;
            const status = document.getElementById('approval-tc-status')?.value;
            const reviewer = document.getElementById('approval-tc-reviewer')?.value.trim();
            const notes = document.getElementById('approval-tc-notes')?.value.trim();

            await this.submitTestCaseApproval(tcId, status, reviewer, notes);
            if (modal) modal.style.display = 'none';
        });
    }

    openTcApprovalModal(tcId, preselectedStatus = 'APPROVED') {
        const modal = document.getElementById('modal-tc-approval');
        const tc = this.testCases.find(t => t.id === parseInt(tcId, 10));
        if (!modal) return;

        document.getElementById('approval-tc-id').value = tcId;
        const titleElem = document.getElementById('approval-modal-tc-title');
        if (titleElem) titleElem.textContent = tc ? `#TC-${tc.id}: ${tc.title}` : `Test Case #${tcId}`;

        const statusSelect = document.getElementById('approval-tc-status');
        if (statusSelect) statusSelect.value = preselectedStatus;

        modal.style.display = 'flex';
    }

    async updateTestCaseStatusQuick(tcId, status) {
        await this.submitTestCaseApproval(tcId, status, "Lead QA Architect", `Quick lifecycle status update to ${status}`);
    }

    async submitTestCaseApproval(tcId, status, reviewer, notes) {
        try {
            const res = await fetch(`/api/testcases/${tcId}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: status,
                    reviewer: reviewer,
                    review_notes: notes
                })
            });

            if (res.ok) {
                const data = await res.json();
                this.loadDashboardData();
            } else {
                alert("Failed to update test case approval status.");
            }
        } catch (err) {
            console.error("Error submitting test case approval:", err);
        }
    }

    viewRunDetails(runId) {
        this.navigateView('runner-view');
        const client = window.runnerClient;
        if (client) {
            client.appendLog(`[Dashboard] Selected Run #${runId}. Fetching logs...`, 'info');
        }
    }

    drawSparklines() {
        // Animate horizontal progress bars
        const successBar = document.getElementById('progress-bar-success');
        const successTextEl = document.getElementById('kpi-success-rate');
        if (successBar && successTextEl) {
            const rawVal = parseFloat(successTextEl.textContent) || 0;
            const pct = Math.min(Math.max(rawVal, 0), 100);
            successBar.style.width = '0%';
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    successBar.style.width = `${pct}%`;
                });
            });
        }

        const coverageBar = document.getElementById('progress-bar-coverage');
        const coverageTextEl = document.getElementById('kpi-code-coverage');
        if (coverageBar && coverageTextEl) {
            const rawVal = parseFloat(coverageTextEl.textContent) || 0;
            const pct = Math.min(Math.max(rawVal, 0), 100);
            coverageBar.style.width = '0%';
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    coverageBar.style.width = `${pct}%`;
                });
            });
        }
    }

    // =========================================================================
    // REQUIREMENTS & AI GENERATION STUDIO
    // =========================================================================
    bindRequirementStudio() {
        const form = document.getElementById('requirement-form');
        const templateSelect = document.getElementById('req-template-select');
        const titleInput = document.getElementById('req-title-input');
        const moduleSelect = document.getElementById('req-module-select');
        const descInput = document.getElementById('req-desc-input');
        const acInput = document.getElementById('req-ac-input');

        const templates = {
            auth: {
                title: "User Authentication & Secure Session Flow",
                module: "Authentication",
                desc: "As a registered shopper, I want to authenticate securely with email and password so I can access saved items and manage account profile.",
                ac: "- Valid credentials authenticate and display user badge\n- Invalid password triggers alert 'Invalid email or password'\n- Empty fields show validation\n- Protect against SQL Injection"
            },
            search: {
                title: "Product Search & Dynamic Catalog Filter",
                module: "Catalog & Search",
                desc: "As a customer, I want to search items by keyword and category filters to locate products rapidly with instant results.",
                ac: "- Matching keyword renders product cards\n- Non-matching queries show 'No products found'\n- Search query string trims leading/trailing spaces"
            },
            checkout: {
                title: "Shopping Cart & 20% Promo Checkout Calculation",
                module: "Cart & Checkout",
                desc: "As a shopper, I want to add products to my cart, apply promo code 'SAVE20', and complete purchase with order confirmation.",
                ac: "- Cart count updates on item addition\n- Applying 'SAVE20' deducts 20% discount from total\n- Order confirmation generates valid Order ID"
            }
        };

        templateSelect?.addEventListener('change', () => {
            const chosen = templates[templateSelect.value];
            if (chosen) {
                titleInput.value = chosen.title;
                moduleSelect.value = chosen.module;
                descInput.value = chosen.desc;
                acInput.value = chosen.ac;
            }
        });

        form?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const checkedTypes = Array.from(document.querySelectorAll('input[name="test_type"]:checked')).map(cb => cb.value);

            const payload = {
                title: titleInput.value.trim(),
                module_name: moduleSelect.value,
                description: descInput.value.trim(),
                acceptance_criteria: acInput.value.trim(),
                test_types: checkedTypes
            };

            const spinner = document.getElementById('ai-generation-loading');
            const container = document.getElementById('generated-testcases-container');
            const countBadge = document.getElementById('generated-count-badge');

            spinner.style.display = 'block';
            container.innerHTML = '';

            try {
                const res = await fetch('/api/generate-testcases', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                spinner.style.display = 'none';

                if (data.test_cases && data.test_cases.length > 0) {
                    countBadge.textContent = `${data.test_cases.length} Cases (${data.provider || 'heuristic'})`;
                    this.renderGeneratedTestCases(data.test_cases);
                    this.loadDashboardData();
                } else {
                    container.innerHTML = `<div class="empty-state-card"><p>Failed to generate test cases. Please try again.</p></div>`;
                }
            } catch (err) {
                spinner.style.display = 'none';
                console.error("Generation error:", err);
                alert("Error connecting to AI generation service.");
            }
        });
    }

    renderGeneratedTestCases(cases) {
        const container = document.getElementById('generated-testcases-container');
        if (!container) return;
        container.innerHTML = '';

        cases.forEach((tc, idx) => {
            const card = document.createElement('div');
            card.className = 'testcase-item-card';
            card.innerHTML = `
                <div class="testcase-item-header">
                    <div class="tc-title-left">
                        <span class="tc-tag ${tc.test_type.toLowerCase()}">${tc.test_type}</span>
                        <span class="badge-tag" style="font-size:0.7rem;">${tc.provider || 'heuristic'}</span>
                        <strong>${tc.title}</strong>
                    </div>
                    <span class="badge-status ${tc.status === 'APPROVED' ? 'passed' : ''}" id="status-badge-${tc.id || idx}">${tc.status || 'DRAFT'}</span>
                </div>
                <div class="testcase-item-body">
                    <div class="gherkin-box">${tc.gherkin_text || 'No Gherkin Defined'}</div>
                    <div style="font-size:0.82rem;color:#94a3b8;margin-bottom:12px;">
                        <strong>Expected:</strong> ${tc.expected_result || 'N/A'}
                    </div>
                    <div class="tc-actions-bar">
                        <button class="btn-xs btn-outline" onclick="app.openEditTcModal(${tc.id})">Edit Scenario</button>
                        <button class="btn-xs btn-cyan" onclick="app.approveTestCase(${tc.id}, this)">✓ Approve for Automation</button>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });
    }

    async approveTestCase(tcId, btnElem) {
        try {
            const res = await fetch(`/api/testcases/${tcId}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'APPROVED', reviewer: 'QA Lead' })
            });
            if (res.ok) {
                btnElem.textContent = '✓ Approved';
                btnElem.classList.remove('btn-cyan');
                btnElem.classList.add('btn-outline');
                const badge = document.getElementById(`status-badge-${tcId}`);
                if (badge) {
                    badge.textContent = 'APPROVED';
                    badge.className = 'badge-status passed';
                }
                this.loadDashboardData();
            }
        } catch (err) {
            console.error("Failed to approve test case:", err);
        }
    }

    // =========================================================================
    // TRACEABILITY MATRIX
    // =========================================================================
    async loadTraceabilityMatrix() {
        const tbody = document.getElementById('traceability-tbody');
        const filterSelect = document.getElementById('filter-traceability-status');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Loading traceability matrix...</td></tr>';

        try {
            const res = await fetch('/api/traceability/matrix');
            const data = await res.json();
            tbody.innerHTML = '';

            if (!data.matrix || data.matrix.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#94a3b8;">No requirements found.</td></tr>';
                return;
            }

            const filterVal = filterSelect ? filterSelect.value.toUpperCase() : 'ALL';

            const filtered = data.matrix.filter(item => {
                const tcs = item.test_cases || [];
                const approvedCount = tcs.filter(t => t.status === 'APPROVED').length;
                let statusCov = 'UNCOVERED';
                if (tcs.length > 0 && approvedCount >= tcs.length) {
                    statusCov = 'COVERED';
                } else if (tcs.length > 0 && approvedCount > 0) {
                    statusCov = 'PARTIALLY_COVERED';
                }

                if (filterVal === 'ALL') return true;
                return statusCov === filterVal;
            });

            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#94a3b8;">No requirements matching selected status filter.</td></tr>';
                return;
            }

            filtered.forEach(item => {
                const req = item.requirement;
                const tcs = item.test_cases || [];
                const approvedCount = tcs.filter(t => t.status === 'APPROVED').length;
                const isCovered = approvedCount > 0;

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>
                        <strong>#REQ-${req.id}</strong><br/>
                        <span>${req.title}</span>
                    </td>
                    <td><span class="badge-tag">${req.module_name}</span></td>
                    <td><code>v${req.version}</code></td>
                    <td>
                        <span style="font-weight:600;">${tcs.length} Total</span> (${approvedCount} Approved)
                    </td>
                    <td>
                        <span class="badge-status ${isCovered ? 'passed' : 'failed'}">
                            ${isCovered ? 'COVERED' : 'UNCOVERED'}
                        </span>
                    </td>
                    <td>
                        ${tcs.some(t => t.latest_result?.status === 'PASSED') ? '<span style="color:#34d399;font-weight:600;">✓ PASSED</span>' : (tcs.some(t => t.latest_result?.status === 'FAILED') ? '<span style="color:#ef4444;font-weight:600;">✗ FAILED</span>' : '<span style="color:#94a3b8;">NOT EXECUTED</span>')}
                    </td>
                    <td>
                        ${tcs.some(t => t.bugs && t.bugs.length > 0) ? '<span class="kpi-pill bug-pill">Defect Linked</span>' : '<span style="color:#34d399;">0 Open</span>'}
                    </td>
                    <td>
                        <button class="btn-xs btn-outline" onclick="app.editRequirement(${req.id})">Edit (Impact)</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (err) {
            console.error("Traceability fetch error:", err);
        }
    }

    // =========================================================================
    // FULL TEST CASES VIEW
    // =========================================================================
    renderFullTestCasesList() {
        const container = document.getElementById('testcases-full-list');
        if (!container) return;
        container.innerHTML = '';

        const typeFilter = document.getElementById('filter-tc-type')?.value || 'ALL';
        const statusFilter = document.getElementById('filter-tc-status')?.value || 'ALL';
        const searchVal = document.getElementById('filter-tc-input')?.value.toLowerCase() || '';

        const filtered = this.testCases.filter(tc => {
            const matchesType = typeFilter === 'ALL' || tc.test_type === typeFilter;
            const matchesStatus = statusFilter === 'ALL' || tc.status === statusFilter;
            const matchesSearch = searchVal === '' || tc.title.toLowerCase().includes(searchVal) || (tc.gherkin_text && tc.gherkin_text.toLowerCase().includes(searchVal));
            return matchesType && matchesStatus && matchesSearch;
        });

        if (filtered.length === 0) {
            container.innerHTML = '<div class="empty-state-card"><p>No test cases match filter criteria.</p></div>';
            return;
        }

        filtered.forEach(tc => {
            const card = document.createElement('div');
            card.className = 'testcase-item-card';
            card.innerHTML = `
                <div class="testcase-item-header">
                    <div class="tc-title-left">
                        <span class="tc-tag ${tc.test_type.toLowerCase()}">${tc.test_type}</span>
                        ${tc.needs_review ? '<span class="kpi-pill bug-pill">NEEDS REVIEW</span>' : ''}
                        <strong>${tc.title}</strong>
                        <small style="color:#64748b;">(Priority: ${tc.priority})</small>
                    </div>
                    <span class="badge-status ${tc.status === 'APPROVED' ? 'passed' : ''}">${tc.status}</span>
                </div>
                <div class="testcase-item-body">
                    <div class="gherkin-box">${tc.gherkin_text || 'No Gherkin'}</div>
                    <div class="tc-actions-bar">
                        <button class="btn-xs btn-outline" onclick="app.openEditTcModal(${tc.id})">Edit</button>
                        ${tc.status !== 'APPROVED' ? `<button class="btn-xs btn-cyan" onclick="app.approveTestCase(${tc.id}, this)">Approve</button>` : ''}
                    </div>
                </div>
            `;
            container.appendChild(card);
        });
    }

    // =========================================================================
    // BUG REPORTS & RCA VIEW
    // =========================================================================
    renderBugReports() {
        const container = document.getElementById('bugs-container');
        const badge = document.getElementById('bug-filter-count-badge');
        const sevSelect = document.getElementById('filter-bug-severity');
        const statusSelect = document.getElementById('filter-bug-status');

        if (!container) return;
        container.innerHTML = '';

        if (this.bugReports.length === 0) {
            if (badge) badge.textContent = "0 Defects Recorded";
            container.innerHTML = '<div class="empty-state-card" style="grid-column:1/-1;"><p>No active bugs recorded. All test assertions are passing!</p></div>';
            return;
        }

        const selectedSev = sevSelect ? sevSelect.value.toUpperCase() : 'ALL';
        const selectedStatus = statusSelect ? statusSelect.value.toUpperCase() : 'ALL';

        const filtered = this.bugReports.filter(b => {
            const bSev = (b.severity || 'MEDIUM').toUpperCase();
            const bStatus = (b.status || 'OPEN').toUpperCase();
            const matchSev = (selectedSev === 'ALL') || (bSev === selectedSev);
            const matchStatus = (selectedStatus === 'ALL') || (bStatus === selectedStatus);
            return matchSev && matchStatus;
        });

        if (badge) {
            badge.textContent = `${filtered.length} of ${this.bugReports.length} Defects Displayed`;
        }

        if (filtered.length === 0) {
            container.innerHTML = '<div class="empty-state-card" style="grid-column:1/-1;"><p>No defects match the selected filter criteria.</p></div>';
            return;
        }

        filtered.forEach(b => {
            const card = document.createElement('div');
            const bSev = (b.severity || 'HIGH').toUpperCase();
            const bStatus = (b.status || 'OPEN').toUpperCase();
            card.className = `bug-card ${bSev.toLowerCase()}`;
            card.innerHTML = `
                <div class="bug-card-header">
                    <div>
                        <span class="badge-tag" style="background:${bStatus === 'RESOLVED' ? '#065f46' : '#7f1d1d'};color:${bStatus === 'RESOLVED' ? '#34d399' : '#fca5a5'};">${bSev}</span>
                        <span class="badge-tag" style="background:#1e293b;color:#cbd5e1;">${bStatus}</span>
                        <span class="badge-tag">${b.module || 'General'}</span>
                    </div>
                    <small style="color:#64748b;">${b.created_at || 'Recent'}</small>
                </div>
                <h4 class="bug-title">${b.title}</h4>
                <p style="font-size:0.85rem;color:#94a3b8;margin-top:6px;">${b.summary || ''}</p>
                <div class="bug-rca-box">
                    <strong style="color:#a855f7;">🤖 AI Root Cause Analysis (RCA):</strong>
                    <p style="margin-top:4px;">${b.root_cause_analysis || 'Under investigation'}</p>
                    <div style="margin-top:8px;border-top:1px solid #1e293b;padding-top:6px;">
                        <strong style="color:#38bdf8;">💡 Suggested Fix:</strong>
                        <p style="margin-top:2px;font-family:var(--font-code);font-size:0.78rem;">${b.ai_fix_suggestion || 'Review element assertions'}</p>
                    </div>
                </div>
                <div class="modal-footer" style="margin-top:0;">
                    <button class="btn-xs btn-outline" onclick="app.copyJiraBugMarkdown(${JSON.stringify(b).replace(/"/g, '&quot;')})">Copy Jira Markdown</button>
                </div>
            `;
            container.appendChild(card);
        });
    }

    copyJiraBugMarkdown(bug) {
        const md = `h2. ${bug.title}\n*Severity:* ${bug.severity || 'CRITICAL'}\n*Module:* ${bug.module || 'General'}\n\nh3. Summary\n${bug.summary || bug.error_message || ''}\n\nh3. Steps to Reproduce\n${bug.steps_to_reproduce || 'Execute automated scenario against test target'}\n\nh3. Root Cause Analysis (AI RCA)\n${bug.root_cause_analysis || 'Under investigation'}\n\nh3. Suggested Fix\n{code:javascript}\n${bug.ai_fix_suggestion || 'Check DOM selectors'}\n{code}`;
        navigator.clipboard.writeText(md).then(() => alert("Copied Jira Bug Markdown to clipboard!"));
    }

    // =========================================================================
    // TEST DATA FACTORY
    // =========================================================================
    async loadTestData() {
        try {
            const res = await fetch('/api/test-data');
            if (!res.ok) return;
            this.datasets = await res.json();

            const emailBody = document.getElementById('email-data-body');
            if (emailBody && this.datasets.emails) {
                emailBody.innerHTML = `
                    <div class="data-pill-list">
                        <div class="data-item-pill"><span>Valid: ${this.datasets.emails.valid[0]}</span></div>
                        <div class="data-item-pill"><span style="color:#f87171;">Invalid: ${this.datasets.emails.invalid_format[0]}</span></div>
                        <div class="data-item-pill"><span style="color:#fbbf24;">Boundary: ${this.datasets.emails.boundary_edge_cases[0]}</span></div>
                        <div class="data-item-pill"><span style="color:#c084fc;">SQLi: ${this.datasets.emails.security_payloads[0]}</span></div>
                    </div>
                `;
            }

            const numBody = document.getElementById('numbers-data-body');
            if (numBody && this.datasets.boundary_numbers) {
                numBody.innerHTML = `
                    <div class="data-pill-list">
                        ${this.datasets.boundary_numbers.slice(0, 4).map(n => `
                            <div class="data-item-pill"><span>${n.label}</span><strong style="color:#38bdf8;">${n.value}</strong></div>
                        `).join('')}
                    </div>
                `;
            }

            const secBody = document.getElementById('security-data-body');
            if (secBody && this.datasets.security_vectors) {
                secBody.innerHTML = `
                    <div class="data-pill-list">
                        ${this.datasets.security_vectors.slice(0, 3).map(s => `
                            <div class="data-item-pill"><span>${s.category}</span><code style="color:#f43f5e;">${s.payload.substring(0, 25)}</code></div>
                        `).join('')}
                    </div>
                `;
            }

            const profBody = document.getElementById('profiles-data-body');
            if (profBody && this.datasets.synthetic_profiles) {
                profBody.innerHTML = `
                    <table class="saas-table">
                        <thead>
                            <tr><th>User ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Mock Card</th></tr>
                        </thead>
                        <tbody>
                            ${this.datasets.synthetic_profiles.map(p => `
                                <tr>
                                    <td><code>${p.id}</code></td>
                                    <td><strong>${p.name}</strong></td>
                                    <td>${p.email}</td>
                                    <td>${p.phone}</td>
                                    <td><code>${p.payment_card}</code></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            }
        } catch (err) {
            console.error("Failed to load test data sets:", err);
        }
    }

    copyDataset(type) {
        if (!this.datasets) return;
        let dataStr = JSON.stringify(this.datasets, null, 2);
        navigator.clipboard.writeText(dataStr).then(() => alert(`Copied ${type} dataset to clipboard!`));
    }

    // =========================================================================
    // CODE STUDIO
    // =========================================================================
    bindCodeStudioTabs() {
        document.querySelectorAll('.code-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.code-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const tabKey = tab.getAttribute('data-tab');
                this.loadCodeStudioContent(tabKey);
            });
        });

        document.getElementById('btn-copy-code')?.addEventListener('click', () => {
            const code = document.getElementById('code-studio-display')?.textContent || '';
            navigator.clipboard.writeText(code).then(() => alert("Code copied to clipboard!"));
        });
    }

    async loadCodeStudioContent(tabKey) {
        const display = document.getElementById('code-studio-display');
        const filenameLabel = document.getElementById('active-code-filename');
        if (!display) return;

        try {
            const res = await fetch(`/api/export/code?type=${tabKey}`);
            const data = await res.json();
            display.textContent = data.code || '// Code preview unavailable';
            if (filenameLabel) filenameLabel.textContent = data.filename || 'CodeFile';
        } catch (err) {
            console.error("Code fetch error:", err);
        }
    }
}

const app = new QAApp();
