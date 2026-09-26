# AI-Powered QA Testing Assistant 🤖⚡

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Selenium](https://img.shields.io/badge/Selenium-4.18+-43B02A?style=for-the-badge&logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![Java](https://img.shields.io/badge/Java-TestNG-ED8B00?style=for-the-badge&logo=java&logoColor=white)](https://testng.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

An enterprise-grade, SaaS-style **AI-Powered Quality Assurance Platform** that accelerates manual and automated testing workflows with AI requirement analysis, Human-in-the-Loop review & approval, real Selenium browser automation, synthetic test data generation, async queue execution, and AI Root Cause Analysis (RCA) defect reporting.

---

## 🌟 Key Highlights & Capabilities

- 🎨 **Dark-Mode Glassmorphic SaaS Dashboard**: Cyberpunk neon cyan (`#00e5ff`) and royal blue glow theme with real-time KPIs (**Measured Success Rate**, **Requirement Coverage**), rectangular progress indicators, mini sparkline charts, and workflow guidance.
- 📋 **Requirements Studio & Multi-Strategy AI Generation**: Generates **Functional**, **Negative**, **Boundary**, and **Security** test cases with Gherkin BDD syntax and step mappings.
- 👤 **Human-in-the-Loop QA Approval**: Review, edit Gherkin steps, and approve test cases before automation execution.
- ⚡ **Dual Automation Execution Engine**:
  - **Real Selenium WebDriver (Headless & Headed)**: Real browser DOM execution with explicit waits (`WebDriverWait`), screenshot capture, and live console logs.
  - **Heuristic Simulation Mode**: Fast in-memory sandbox for offline or headless environments without Chrome binaries, clearly labeled with simulation badges.
- 🔄 **Asynchronous Execution Queue**: Background thread pool worker supporting job states (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `TIMED_OUT`) with live polling and cancel support.
- 🔗 **Traceability Matrix & Impact Analysis**: End-to-end traceability linking Requirements → Test Cases → Test Runs → Defect Reports. Flagging linked tests as `NEEDS_REVIEW` on requirement updates.
- 🐞 **AI Root Cause Analysis (RCA) Bug Reporter**: Automated stack trace triage, severity classification, and 1-click **Jira / GitHub Markdown** export.
- 🛡️ **Centralized SSRF & URL Safety Validation**: Enforces strict protocol checks (HTTP/HTTPS only), blocks cloud metadata endpoints (`169.254.169.254`), private IP restrictions, and domain allowlists.
- 🔒 **Session Security & RBAC**: PBKDF2:SHA256 password hashing, secure session management, and cross-user isolation.
- 🧬 **Synthetic QA Test Data Factory**: Pre-built matrices for email boundary testing, password resilience, SQL injection vectors, and realistic user profiles.
- ☕ **Java + Selenium + TestNG Code Studio**: Auto-generates enterprise Page Object Model (POM) classes, `pom.xml`, `testng.xml`, and PyTest scripts.
- 🛒 **Built-in Target E-Commerce Sandbox (`/app/target-store`)**: Interactive tech store (*ApexCart*) with user login, search, cart, coupon discounts, and an interactive **Bug Simulation Switch** for live demonstration.

---

## 🏗️ Architecture & 3-Tier Layering

```
[Layer 1: Frontend (QA Dashboard & Target Store)]
       ↓ HTTP REST API (JSON) + Cookie Session
[Layer 2: Backend (Flask Core Logic, Auth & SSRF Validation)]
       ↓
[Layer 3: Services & Engines]
├── AI Engine (Google Gemini / OpenAI / Offline Domain Heuristics)
├── Asynchronous Execution Queue (ThreadPoolExecutor + Status Polling)
├── Selenium Automation Engine (Chrome WebDriver / Simulation Fallback)
├── Java + TestNG POM Code Generator
└── Database & Repository Layer (SQLite with Foreign Keys & Migrations)
```

---

## 📁 Repository Structure

```
AI-Powered-QA-Testing-Assistant/
├── templates/                 # Frontend Jinja2 HTML Templates
│   ├── index.html             # Main SaaS Dashboard UI
│   └── target_app.html        # Embedded Target E-Commerce Store
├── static/                    # Frontend Styles & Scripts
│   ├── css/
│   │   ├── style.css          # Dark-mode glassmorphic theme
│   │   └── target_app.css     # Target store styling
│   ├── js/
│   │   ├── app.js             # Dashboard state & KPI sparkline rendering
│   │   ├── ai_assistant.js    # Interactive AI Copilot chat drawer
│   │   ├── test_runner.js     # Live execution console & screenshot modal
│   │   └── target_app.js      # Target store client logic
│   └── screenshots/           # Execution screenshots & diagnostic artifacts
├── engine/                    # Core Backend Services
│   ├── ai_generator.py        # AI Gherkin, test case & RCA generator
│   ├── execution_queue.py     # Asynchronous job queue & worker manager
│   ├── selenium_runner.py     # Selenium WebDriver test execution engine
│   ├── java_generator.py      # Java TestNG POM & PyTest code exporter
│   └── test_data_factory.py   # Synthetic QA test dataset generator
├── database/                  # Database Schema & SQLite manager
│   ├── db.py
│   └── schema.sql
├── automation/                # Java + Selenium + TestNG Framework
│   ├── pom.xml                # Maven configuration
│   ├── testng.xml             # TestNG test suite configuration
│   └── src/
│       ├── main/java/com/qaplatform/pages/    # Page Object Model classes
│       └── test/java/com/qaplatform/tests/    # TestNG test cases
├── docs/                      # Technical Documentation
│   ├── ARCHITECTURE.md        # Detailed 3-tier architecture guide
│   ├── WORKFLOW.md            # Human-in-the-Loop workflow explanation
│   ├── ACCEPTANCE_TESTS.md    # Acceptance check verification matrix
│   └── INTERVIEW_PREP.md      # QA interview preparation talking points
├── tests/                     # Automated PyTest Test Suite
│   └── test_platform.py
├── auth.py                    # Session authentication, hashing & CSRF
├── url_validator.py           # SSRF protection & safe target URL validator
├── config.py                  # Server & AI configurations
├── database.py                # Primary database schema & migrations
├── app.py                     # Flask application entry point & REST APIs
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore
└── README.md
```

---

## 🚀 Quick Setup & Installation

### 1. Prerequisites
- **Python**: 3.10+ installed
- **Google Chrome** & **ChromeDriver**: Optional for live headless/headed browser testing (fallback simulation works out of the box).
- **Java JDK 11+ & Maven**: Optional for running exported Java TestNG test suites.

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/your-username/AI-Powered-QA-Testing-Assistant.git
cd AI-Powered-QA-Testing-Assistant

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` (optional for local testing, required for cloud LLMs):
```bash
cp .env.example .env
```
Key configuration settings in `.env`:
- `SECRET_KEY`: Random 32+ character string for Flask session encryption.
- `AI_PROVIDER`: Choose active AI mode (`auto`, `gemini`, `openai`, `heuristic`). Default is `auto` (uses cloud LLM if key is present, otherwise falls back gracefully to offline heuristics).
- `GEMINI_API_KEY`: (Optional) Google Gemini API key (`gemini-3.8-flash`) for live contextual BDD test generation and RCA.
- `OPENAI_API_KEY`: (Optional) OpenAI API key (`gpt-4o-mini`).
- `ALLOW_EXTERNAL_TARGET_URLS`: Set to `True` to allow testing external whitelisted staging URLs.

> 🔒 **Security Note**: API keys are read strictly from server-side environment variables and are **never** exposed in HTML, JavaScript, API payloads, or client telemetry.

---

## 🔑 Gemini API Key Setup

### Step 1 — Get your free Gemini API key
1. Open **[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)** in a browser.
2. Sign in with your Google account.
3. Click **"Create API key"** → choose a project → click **"Create API key in existing project"**.
4. Copy the key (starts with `AIza...`).

### Step 2 — Create your `.env` file
```bash
# Windows (PowerShell)
copy .env.example .env
```
Open `.env` and set:
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...your-real-key...
AI_FALLBACK_ENABLED=true
```

> ⚠️ **The `.env` file is listed in `.gitignore` and will never be committed to Git.**
> Never paste your API key into `app.py`, `config.py`, or any client-facing file.

### Step 3 — Install the official google-genai SDK
```bash
pip install google-genai
```
Or install all requirements at once:
```bash
pip install -r requirements.txt
```

---

## 🤖 AI Provider & Fallback Architecture

The platform implements a transparent 3-provider architecture using the official **`google-genai`** Python SDK:
1. **Google Gemini (`gemini-3.8-flash`)**: High-accuracy cloud generation of BDD test scenarios, root cause analysis, and interactive QA advice. Uses the official `google.genai.Client` — **not** raw HTTP calls.
2. **OpenAI (`gpt-4o-mini`)**: Alternative cloud provider with JSON schema adherence.
3. **Offline Heuristic Rule-Engine**: High-speed, deterministic, zero-cost fallback engine that operates with zero API key dependencies.

**`AI_FALLBACK_ENABLED`** controls the safety net:
- `true` (default) → If Gemini/OpenAI fails for any reason, the Offline Heuristic Engine silently takes over.
- `false` → Errors surface immediately without heuristic substitution (useful for strict integration tests).

```
       [Requirement Ingestion]
                  │
     ┌────────────▼────────────┐
     │ Is Online Provider Key  │
     │ Configured & Available? │
     └──────┬────────────┬─────┘
       YES  │            │ NO / Timeout / Rate Limit / Malformed
            ▼            ▼
   ┌─────────────────┐ ┌───────────────────────────┐
   │ Google Gemini / │ │ Offline Heuristic Engine  │
   │ OpenAI LLM API  │ │ (Deterministic QA Rules)  │
   └────────┬────────┘ └─────────────┬─────────────┘
            │                        │
            ▼                        ▼
   [Schema Validation]    [Stamped: offline-heuristic]
   [Action Allowlist ]    [Explicit Fallback Telemetry]
```

---

### 4. Start the Application

#### Development Mode:
```bash
# Make sure your .env exists (copy from .env.example)
python app.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your web browser.

The dashboard will display one of three status labels:
| Dashboard Label | Meaning |
|---|---|
| `ONLINE — Gemini AI` | Real Gemini API key configured and last call succeeded |
| `FALLBACK — Offline Heuristic` | Gemini key valid but call failed; heuristics used |
| `UNAVAILABLE — Gemini unavailable` | No valid `GEMINI_API_KEY` in environment |

#### Production Deployment:
> ⚠️ **Important**: Do not use the Flask development server (`python app.py`) in production.

For Windows production deployment (Waitress WSGI):
```bash
pip install waitress
waitress-serve --listen=127.0.0.1:5000 app:app
```

For Linux production deployment (Gunicorn WSGI):
```bash
pip install gunicorn
gunicorn --workers=4 --threads=2 --bind=0.0.0.0:5000 --access-logfile - app:app
```

---

## 🧪 Automated Testing & Verification

Run the full platform test suite with pytest:
```bash
python -m pytest -v
```

This verifies:
- User registration, password hashing (PBKDF2:SHA256), and session auth
- Cross-user authorization and access control
- SSRF prevention, scheme blocking, and cloud metadata defense
- Asynchronous execution queue, polling, timeout, and cancellation
- Requirement traceability, impact analysis, and `NEEDS_REVIEW` workflow
- AI test case schema validation and action allowlist enforcement
- Java TestNG identifier sanitization and keyword escaping
- Selenium execution mode flags and simulation metric separation
- **Google-genai SDK integration** (tests 18, 18b, 19, 20)
- **Dashboard label semantics** (tests 21a, 21b, 21c)
- **`AI_FALLBACK_ENABLED=false` strict mode** (test 23)
- **Telemetry fields** (`provider_used`, `model`, `latency_ms`, `fallback_used`, `status`) (test 24)

---

## 🔍 Verifying a Real Gemini API Request

### Method 1 — Watch the console log
```bash
python app.py
```
Generate test cases via the dashboard. The server console will print:
```
[AI Engine] Provider: gemini-3.8-flash  Latency: 847.2 ms  Status: SUCCESS
```
If you see `offline-heuristic` instead, check that `GEMINI_API_KEY` is correctly set in `.env`.

### Method 2 — Poll the AI status API
```bash
curl http://127.0.0.1:5000/api/ai/status
```
Expect:
```json
{
  "dashboard_label": "ONLINE — Gemini AI",
  "provider_code": "gemini-3.8-flash",
  "model_name": "gemini-3.8-flash",
  "last_generation": {
    "status": "SUCCESS",
    "fallback_used": false,
    "latency_ms": 847.2
  }
}
```
A `dashboard_label` of `"ONLINE — Gemini AI"` with `"fallback_used": false` and a real measured `latency_ms` confirms the Gemini API was called for the last generation.

### Method 3 — Run the SDK import test
```bash
python -m pytest tests/test_platform.py::test_google_genai_sdk_importable -v
```
This will `PASSED` if `google-genai` is correctly installed.

---

## ⚙️ Execution Modes

1. **`SELENIUM_HEADLESS`**: Spawns a real Chrome browser in headless mode. Executes real DOM events and collects actual screenshots.
2. **`SELENIUM_HEADED`**: Spawns a visible Chrome browser window.
3. **`HEURISTIC_SIMULATION`**: An in-memory sandbox that executes action sequences safely without requiring Chrome/ChromeDriver binaries. Results are explicitly flagged with `is_simulated = 1` and labeled in reports.

---

## 📑 License
This project is open source and available under the [MIT License](LICENSE).

