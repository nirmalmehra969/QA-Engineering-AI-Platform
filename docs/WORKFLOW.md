# QA Testing Workflow & AI Role Division

## 1. The Human-in-the-Loop Workflow

```
[Requirement Ingestion]
       ↓
[AI-Assisted Test Design]
       ↓
[Tester Review & Approval]
       ↓
[Selenium Automation Execution]
       ↓
[Verified Results & Bug Reports]
```

1. **Requirement Ingestion**: The QA tester inputs product requirements or user stories into the Requirement Studio.
2. **AI-Assisted Test Design**: The AI service analyzes the acceptance criteria and generates positive, negative, boundary, and security test cases in Gherkin BDD syntax.
3. **Tester Review & Approval**: The human tester reviews each scenario, edits parameters if necessary, and marks the test case as `APPROVED`.
4. **Selenium Automation Execution**: The automation engine runs approved test cases against the target web application with real browser interactions.
5. **Verified Results & Bug Reports**: The system records pass/fail metrics, execution timings, and failure screenshots. The AI analyzes failure logs and generates Jira-ready Bug Reports with Root Cause Analysis (RCA).

---

## 2. Where AI is Used vs Conventional Code

This distinction is fundamental to modern, enterprise-grade AI testing platforms:

| Feature Area | AI's Role (Probabilistic / Generative) | Conventional Code's Role (Deterministic / Rule-Based) |
| :--- | :--- | :--- |
| **Test Case Generation** | Suggests test scenarios and Gherkin steps from raw requirements. | Validates schema structure, checks uniqueness, and saves to database. |
| **Test Data Generation** | Suggests input variations, edge cases, and injection strings. | Enforces data constraints, regex validation, and type safety. |
| **Browser Automation** | Proposes action mappings from natural language steps. | Selenium executes actual browser commands, waits, and assertions. |
| **Bug Analysis & RCA** | Summarizes stack traces, classifies severity, and suggests code fixes. | Records actual status code, logs, and failure screenshot evidence. |
| **Dashboard & Metrics** | Provides conversational test summaries and QA insights. | Calculates numerical pass/fail rates, code coverage, and execution durations. |
