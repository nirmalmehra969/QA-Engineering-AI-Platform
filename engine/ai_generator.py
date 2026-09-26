import json
import re
import os
import requests
from config import GEMINI_API_KEY, OPENAI_API_KEY, AI_PROVIDER, AI_FALLBACK_ENABLED, GEMINI_MODEL_NAME

# ── Official Google Generative AI SDK ─────────────────────────────────────────
# Imported lazily inside GeminiLLMProvider so the app still boots even when
# google-genai is not yet installed (graceful degradation to heuristics).
# ─────────────────────────────────────────────────────────────────────────────


REQUIRED_TC_FIELDS = {"title", "test_type", "priority", "gherkin_text", "steps_json", "expected_result"}
ALLOWED_TEST_TYPES = {"Functional", "Negative", "Boundary", "Security", "Performance", "UI"}
VALID_ACTIONS = {
    "navigate",
    "click",
    "input",
    "clear",
    "assert_text",
    "assert_visible",
    "assert_not_visible",
    "assert_count_gt",
    "assert_disabled"
}

class BaseAIProvider:
    """Abstract Base Class for AI Test Case and Defect Generation Providers."""
    def __init__(self, provider_code, display_name, is_online=False):
        self.provider_code = provider_code
        self.display_name = display_name
        self.is_online = is_online

    def check_availability(self):
        """Returns (is_available: bool, message: str)"""
        raise NotImplementedError

    def generate_test_cases(self, title, description, module_name, acceptance_criteria, test_types):
        """Returns (test_cases_list, error_or_none)"""
        raise NotImplementedError

    def analyze_failure_rca(self, test_title, error_message, stack_trace="", browser_logs=""):
        """Returns (rca_dict, error_or_none)"""
        raise NotImplementedError

    def chat(self, user_message, history=None):
        """Returns (reply_dict, error_or_none)"""
        raise NotImplementedError


class OfflineHeuristicProvider(BaseAIProvider):
    """
    Offline Rule-Based Deterministic QA Heuristic Engine.
    Works with zero external dependencies and zero API costs.
    """
    def __init__(self):
        super().__init__(
            provider_code="offline-heuristic",
            display_name="Offline QA Heuristic Engine",
            is_online=False
        )

    def check_availability(self):
        return True, "Deterministic offline heuristic rule-engine active and operational."

    def generate_test_cases(self, title, description, module_name, acceptance_criteria, test_types):
        title_lower = str(title).lower()
        desc_lower = str(description).lower()
        module_lower = str(module_name).lower()

        test_cases = []

        # Domain 1: Authentication / Login / Signup
        if any(k in title_lower or k in desc_lower or k in module_lower for k in ["login", "auth", "signin", "password", "register", "signup"]):
            if "Functional" in test_types:
                test_cases.append({
                    "title": f"Verify successful authentication with valid credentials for {title}",
                    "test_type": "Functional",
                    "priority": "High",
                    "gherkin_text": f"Feature: {module_name} Authentication\n  Scenario: Valid Login\n    Given the user opens the application login screen\n    When the user enters a registered email and correct password\n    And clicks on the 'Sign In' button\n    Then the system redirects to the user dashboard\n    And displays an active session badge with user profile",
                    "pre_conditions": "User is registered with active credentials 'demo@qa-platform.io' / 'Password@123'",
                    "steps_json": [
                        {"action": "navigate", "target": "/app/target-store", "value": ""},
                        {"action": "click", "target": "#nav-login-btn", "value": ""},
                        {"action": "input", "target": "#login-email", "value": "demo@qa-platform.io"},
                        {"action": "input", "target": "#login-password", "value": "Password@123"},
                        {"action": "click", "target": "#login-submit-btn", "value": ""},
                        {"action": "assert_text", "target": "#user-profile-badge", "value": "Welcome, Demo Tester"}
                    ],
                    "expected_result": "Authentication completes within 2s, redirects to dashboard with valid session."
                })

            if "Negative" in test_types:
                test_cases.append({
                    "title": f"Verify login rejection and error messaging with incorrect password",
                    "test_type": "Negative",
                    "priority": "High",
                    "gherkin_text": f"Feature: {module_name} Authentication\n  Scenario: Invalid Password Attempt\n    Given the user is on the login dialog\n    When the user enters an invalid password 'WrongPass!99'\n    And submits the login form\n    Then an alert stating 'Invalid email or password' is shown\n    And user remains unauthenticated",
                    "pre_conditions": "User is on the login view",
                    "steps_json": [
                        {"action": "navigate", "target": "/app/target-store", "value": ""},
                        {"action": "click", "target": "#nav-login-btn", "value": ""},
                        {"action": "input", "target": "#login-email", "value": "demo@qa-platform.io"},
                        {"action": "input", "target": "#login-password", "value": "WrongPassword999"},
                        {"action": "click", "target": "#login-submit-btn", "value": ""},
                        {"action": "assert_visible", "target": "#login-error-alert", "value": ""}
                    ],
                    "expected_result": "System prevents unauthorized access and displays contextual validation error."
                })

            if "Boundary" in test_types:
                test_cases.append({
                    "title": "Verify form validation when submitting empty required fields",
                    "test_type": "Boundary",
                    "priority": "Medium",
                    "gherkin_text": f"Feature: {module_name} Authentication\n  Scenario: Empty Inputs Validation\n    Given the login modal is displayed\n    When the user submits the form with empty email and password\n    Then inline validation warnings highlight required fields",
                    "pre_conditions": "Login modal is opened with blank fields",
                    "steps_json": [
                        {"action": "navigate", "target": "/app/target-store", "value": ""},
                        {"action": "click", "target": "#nav-login-btn", "value": ""},
                        {"action": "input", "target": "#login-email", "value": ""},
                        {"action": "input", "target": "#login-password", "value": ""},
                        {"action": "click", "target": "#login-submit-btn", "value": ""},
                        {"action": "assert_visible", "target": ".field-validation-error", "value": ""}
                    ],
                    "expected_result": "Client validation markers highlight empty email and password inputs."
                })

            if "Security" in test_types:
                test_cases.append({
                    "title": "Verify SQL Injection resilience in authentication fields",
                    "test_type": "Security",
                    "priority": "Critical",
                    "gherkin_text": f"Feature: {module_name} Security\n  Scenario: SQL Injection Sanitization\n    Given the user is on the login page\n    When the user enters \"' OR '1'='1' --\" in the username\n    And submits the form\n    Then the system safely rejects the payload without database disclosure",
                    "pre_conditions": "Target endpoint active",
                    "steps_json": [
                        {"action": "navigate", "target": "/app/target-store", "value": ""},
                        {"action": "click", "target": "#nav-login-btn", "value": ""},
                        {"action": "input", "target": "#login-email", "value": "' OR '1'='1' --"},
                        {"action": "input", "target": "#login-password", "value": "test1234"},
                        {"action": "click", "target": "#login-submit-btn", "value": ""},
                        {"action": "assert_visible", "target": "#login-error-alert", "value": ""}
                    ],
                    "expected_result": "Server sanitizes input and safely rejects with standard 401 response."
                })

        # Domain 2: Search & Filter
        elif any(k in title_lower or k in desc_lower or k in module_lower for k in ["search", "filter", "catalog", "product"]):
            if "Functional" in test_types:
                test_cases.append({
                    "title": f"Verify real-time product search matching keyword for {title}",
                    "test_type": "Functional",
                    "priority": "High",
                    "gherkin_text": f"Feature: Product Catalog Search\n  Scenario: Keyword Product Search\n    Given the customer is on the catalog page\n    When the customer searches for 'Wireless Headphones'\n    Then products containing 'Wireless Headphones' are displayed",
                    "pre_conditions": "Catalog contains products matching 'Wireless Headphones'",
                    "steps_json": [
                        {"action": "navigate", "target": "/app/target-store", "value": ""},
                        {"action": "input", "target": "#search-input", "value": "Wireless Headphones"},
                        {"action": "click", "target": "#search-btn", "value": ""},
                        {"action": "assert_count_gt", "target": ".product-card", "value": "0"}
                    ],
                    "expected_result": "Catalog filters and shows matching product cards instantly."
                })

            if "Negative" in test_types:
                test_cases.append({
                    "title": "Verify non-existent product search displays 'No Results Found' gracefully",
                    "test_type": "Negative",
                    "priority": "Medium",
                    "gherkin_text": f"Feature: Product Catalog Search\n  Scenario: Non-existent Query Search\n    Given the customer is on the product listing\n    When the customer searches for 'XYZNONEXISTENT999'\n    Then an empty state message with 'No products found' is rendered",
                    "pre_conditions": "Catalog is loaded",
                    "steps_json": [
                        {"action": "navigate", "target": "/app/target-store", "value": ""},
                        {"action": "input", "target": "#search-input", "value": "XYZNONEXISTENT999"},
                        {"action": "click", "target": "#search-btn", "value": ""},
                        {"action": "assert_visible", "target": "#no-results-msg", "value": ""}
                    ],
                    "expected_result": "Empty state UI renders without crashing or hanging."
                })

        # Domain 3: Shopping Cart, Order & Checkout
        else:
            if "Functional" in test_types:
                test_cases.append({
                    "title": f"Verify item addition to cart and checkout for {title}",
                    "test_type": "Functional",
                    "priority": "High",
                    "gherkin_text": f"Feature: Shopping Cart Workflow\n  Scenario: Add Product to Cart\n    Given the customer views product catalog\n    When the customer clicks 'Add to Cart' on an item\n    Then cart badge increments by 1\n    And checkout modal displays item with correct price",
                    "pre_conditions": "Catalog has products in stock",
                    "steps_json": [
                        {"action": "navigate", "target": "/app/target-store", "value": ""},
                        {"action": "click", "target": ".add-to-cart-btn:first-of-type", "value": ""},
                        {"action": "assert_text", "target": "#cart-badge-count", "value": "1"},
                        {"action": "click", "target": "#cart-icon-btn", "value": ""},
                        {"action": "click", "target": "#checkout-btn", "value": ""},
                        {"action": "assert_visible", "target": "#checkout-modal", "value": ""}
                    ],
                    "expected_result": "Cart counter increments and checkout dialog loads with cart total."
                })

            if "Boundary" in test_types:
                test_cases.append({
                    "title": "Verify promo discount coupon calculation on checkout total",
                    "test_type": "Boundary",
                    "priority": "High",
                    "gherkin_text": f"Feature: Checkout Discounts\n  Scenario: Apply 20% Coupon Code\n    Given customer has items in cart\n    When customer applies promo code 'SAVE20'\n    Then subtotal reduces by 20%\n    And order total price updates",
                    "pre_conditions": "Cart has items with subtotal > $0",
                    "steps_json": [
                        {"action": "navigate", "target": "/app/target-store", "value": ""},
                        {"action": "click", "target": ".add-to-cart-btn:first-of-type", "value": ""},
                        {"action": "click", "target": "#cart-icon-btn", "value": ""},
                        {"action": "input", "target": "#promo-input", "value": "SAVE20"},
                        {"action": "click", "target": "#apply-promo-btn", "value": ""},
                        {"action": "assert_visible", "target": "#discount-badge", "value": ""}
                    ],
                    "expected_result": "Discount reduces total and displays 20% discount badge."
                })

        return test_cases, None

    def analyze_failure_rca(self, test_title, error_message, stack_trace="", browser_logs=""):
        err_lower = (error_message or "").lower() + " " + (stack_trace or "").lower()

        severity = "Medium"
        module = "General UI / Backend"
        summary = f"Automated test failure during execution of '{test_title}'"
        root_cause = "Assertion condition on DOM element failed to evaluate to true."
        fix_suggestion = "Inspect DOM selector and synchronize backend state."

        if "login" in test_title.lower() or "auth" in test_title.lower():
            module = "Authentication Service"
            if "timeout" in err_lower or "not visible" in err_lower:
                severity = "Critical"
                root_cause = "Element selector failed to render within wait timeout, suggesting potential session state deadlock."
                fix_suggestion = "Verify modal transition timing and ensure `#user-profile-badge` has explicit WebDriverWait."
            else:
                severity = "High"
                root_cause = "Authentication token was not established following credential submission."
                fix_suggestion = "Verify `/api/auth/login` sets secure session cookie and returns 200 OK."

        elif "checkout" in test_title.lower() or "discount" in test_title.lower() or "promo" in err_lower:
            module = "Cart & Checkout Engine"
            severity = "High"
            root_cause = "Coupon application state was not propagated to the invoice recalculation handler."
            fix_suggestion = "In checkout controller, bind discount trigger to `updateSummary({ discount: 0.20 })`."

        elif "search" in test_title.lower():
            module = "Catalog & Search"
            severity = "Medium"
            root_cause = "Search query handler returned empty result set on valid keyword substring."
            fix_suggestion = "Ensure catalog filter uses case-insensitive substring matching."

        steps_repro = f"1. Open target application\n2. Trigger workflow for '{test_title}'\n3. Execute assertion against target element\n4. Error observed: {error_message or 'Assertion failed'}"

        return {
            "title": f"[BUG] {test_title} - {(error_message or 'Assertion Failure')[:60]}",
            "severity": severity,
            "module": module,
            "summary": summary,
            "steps_to_reproduce": steps_repro,
            "actual_result": f"Execution failed with error: {error_message or 'Condition not satisfied'}",
            "expected_result": "Test assertions should pass cleanly without exceptions.",
            "root_cause_analysis": root_cause,
            "ai_fix_suggestion": fix_suggestion
        }, None

    def chat(self, user_message, history=None):
        msg_lower = user_message.lower()

        if "gherkin" in msg_lower or "scenario" in msg_lower:
            reply = ("Here is a standard Gherkin BDD scenario for user checkout:\n\n"
                     "```gherkin\n"
                     "Feature: E-Commerce Checkout\n"
                     "  Scenario: Apply discount and complete order\n"
                     "    Given customer has added items to cart\n"
                     "    When customer enters coupon 'SAVE20'\n"
                     "    And clicks 'Confirm & Pay'\n"
                     "    Then system renders order confirmation receipt with Order ID\n"
                     "```\n\nYou can add this scenario to your test suite anytime!")
        elif "bug" in msg_lower or "rca" in msg_lower:
            reply = "Our AI Root Cause Analysis (RCA) engine inspects WebDriver console logs, DOM snapshots, and assertion stack traces to pinpoint the exact failure line and suggest a code fix. Reports can be exported directly to Jira!"
        else:
            reply = "Hello! I am your **AI QA Assistant Copilot** (Offline Mode). I can generate Gherkin scenarios, Java TestNG Page Objects, security injection payloads, and diagnose test failure logs without external API dependency."

        return {
            "reply": reply,
            "provider": self.provider_code,
            "display_name": self.display_name,
            "is_online": False
        }, None


class GeminiLLMProvider(BaseAIProvider):
    """
    Google Gemini Cloud LLM Provider — uses the official google-genai Python SDK.

    Security contract:
    - GEMINI_API_KEY is read exclusively from environment variables / config.
    - The key is NEVER returned in API responses, logs, or any client-visible data.
    - All network I/O is TLS-encrypted and occurs server-side only.

    Telemetry recorded per request:
    - provider      : 'gemini-3.8-flash' (or configured model)
    - model         : actual model identifier returned / configured
    - latency_ms    : wall-clock milliseconds measured by perf_counter
    - fallback_used : True only when heuristic engine substituted for Gemini
    - status        : 'SUCCESS' | 'RATE_LIMITED' | 'AUTH_FAILED' | 'TIMEOUT' |
                      'NETWORK_ERROR' | 'MALFORMED_RESPONSE' | 'NO_API_KEY'
    """

    # Dashboard label constants — shown in /api/ai/status
    LABEL_ONLINE   = "ONLINE — Gemini AI"
    LABEL_FALLBACK = "FALLBACK — Offline Heuristic"
    LABEL_NO_KEY   = "UNAVAILABLE — Gemini unavailable"

    def __init__(self, api_key=None):
        super().__init__(
            provider_code=GEMINI_MODEL_NAME,
            display_name=f"Google Gemini ({GEMINI_MODEL_NAME})",
            is_online=True
        )
        # Key resolved at call-time via os.environ; stored only as fallback.
        self._init_api_key = api_key or ""

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _resolve_key(self):
        """Returns the live API key from environment; never exposes it externally."""
        return os.environ.get("GEMINI_API_KEY", "") or self._init_api_key or GEMINI_API_KEY

    def _key_is_valid(self, key):
        """Sanity-checks that the key looks like a real credential, not a placeholder."""
        placeholders = (
            "your_gemini_api_key_here",
            "your_key_here",
            "AIzaSyFake",
        )
        if not key or len(key) < 10:
            return False
        return not any(key.startswith(p) for p in placeholders)

    def _build_client(self, key):
        """
        Constructs a google.genai.Client using the official SDK.
        Raises ImportError if google-genai is not installed.
        """
        try:
            from google import genai  # official google-genai SDK
            return genai.Client(api_key=key)
        except ImportError as exc:
            raise ImportError(
                "The 'google-genai' package is required for Gemini integration. "
                "Install it with: pip install google-genai"
            ) from exc

    # ── Public interface ──────────────────────────────────────────────────────

    def check_availability(self):
        key = self._resolve_key()
        if not self._key_is_valid(key):
            return False, self.LABEL_NO_KEY
        return True, "Gemini API key is configured and ready for live cloud inference."

    def generate_test_cases(self, title, description, module_name, acceptance_criteria, test_types):
        """
        Sends a structured prompt to Gemini via google-genai SDK and returns
        validated QA test cases.  Returns (cases_list, None) on success or
        (None, error_string) on any failure — never raises.
        """
        key = self._resolve_key()
        if not self._key_is_valid(key):
            return None, f"[{self.LABEL_NO_KEY}] Set GEMINI_API_KEY in your .env file."

        prompt = (
            "You are a Principal Software QA Automation Architect.\n"
            f"Generate structured QA automation test cases for:\n"
            f"Title: {title} | Module: {module_name}\n"
            f"Description: {description}\n"
            f"Acceptance Criteria: {acceptance_criteria}\n"
            f"Test Types: {', '.join(test_types)}\n\n"
            "Return ONLY a valid JSON array of objects. "
            "Each object MUST have these exact keys:\n"
            '- "title": (string)\n'
            '- "test_type": (one of: Functional, Negative, Boundary, Security)\n'
            '- "priority": (one of: Critical, High, Medium, Low)\n'
            '- "gherkin_text": (string BDD format)\n'
            '- "pre_conditions": (string)\n'
            '- "steps_json": (array of step objects with "action", "target", "value")\n'
            '- "expected_result": (string)\n\n'
            "Allowed step actions are strictly: "
            "navigate, click, input, clear, assert_text, assert_visible, "
            "assert_not_visible, assert_count_gt, assert_disabled."
        )

        try:
            client = self._build_client(key)
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
                config={
                    "temperature": 0.2,
                    "response_mime_type": "application/json",
                },
            )
            raw_text = response.text
            test_cases = json.loads(raw_text)
            if not isinstance(test_cases, list):
                return None, "Malformed Gemini response: expected a JSON array at top level."
            return test_cases, None

        except ImportError as exc:
            return None, f"google-genai SDK not installed: {exc}"
        except json.JSONDecodeError as jde:
            return None, f"Malformed JSON from Gemini API: {jde}"
        except Exception as exc:
            err = str(exc)
            if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                return None, f"Gemini API rate limit / quota exceeded: {err}"
            if "401" in err or "403" in err or "invalid api key" in err.lower():
                return None, f"Gemini API authentication failed: {err}"
            if "timeout" in err.lower() or "deadline" in err.lower():
                return None, f"Gemini API request timed out: {err}"
            return None, f"Gemini API request error: {err}"

    def analyze_failure_rca(self, test_title, error_message, stack_trace="", browser_logs=""):
        """Calls Gemini for Root Cause Analysis. Returns (rca_dict, None) or (None, error)."""
        key = self._resolve_key()
        if not self._key_is_valid(key):
            return None, f"[{self.LABEL_NO_KEY}] Set GEMINI_API_KEY in your .env file."

        prompt = (
            "You are a Lead QA Architect performing Root Cause Analysis (RCA).\n"
            f"Test Title: {test_title}\n"
            f"Error Message: {error_message}\n"
            f"Stack Trace: {stack_trace}\n"
            f"Browser Logs: {browser_logs}\n\n"
            "Return ONLY a JSON object with:\n"
            '- "title": (string, concise bug title)\n'
            '- "severity": (one of: Critical, High, Medium, Low)\n'
            '- "module": (string)\n'
            '- "summary": (string)\n'
            '- "steps_to_reproduce": (string)\n'
            '- "actual_result": (string)\n'
            '- "expected_result": (string)\n'
            '- "root_cause_analysis": (string explaining the underlying defect)\n'
            '- "ai_fix_suggestion": (string with code fix advice)'
        )

        try:
            client = self._build_client(key)
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
                config={
                    "temperature": 0.2,
                    "response_mime_type": "application/json",
                },
            )
            rca_dict = json.loads(response.text)
            return rca_dict, None
        except ImportError as exc:
            return None, f"google-genai SDK not installed: {exc}"
        except json.JSONDecodeError as jde:
            return None, f"Malformed Gemini RCA JSON: {jde}"
        except Exception as exc:
            return None, f"Gemini RCA error: {str(exc)}"

    def chat(self, user_message, history=None):
        """Conversational QA Copilot via Gemini. Returns (reply_dict, None) or (None, error)."""
        key = self._resolve_key()
        if not self._key_is_valid(key):
            return None, f"[{self.LABEL_NO_KEY}] Set GEMINI_API_KEY in your .env file."

        prompt = (
            "You are the AI QA Assistant Copilot, an expert in software testing, "
            "Gherkin BDD, Selenium WebDriver, and TestNG.\n"
            f"User Question: {user_message}\n"
            "Answer with concise, practical advice, code snippets if requested, "
            "and standard QA best practices."
        )

        try:
            client = self._build_client(key)
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
                config={"temperature": 0.4},
            )
            return {
                "reply": response.text,
                "provider": self.provider_code,
                "display_name": self.display_name,
                "is_online": True,
            }, None
        except ImportError as exc:
            return None, f"google-genai SDK not installed: {exc}"
        except Exception as exc:
            return None, f"Gemini chat error: {str(exc)}"


class OpenAILLMProvider(BaseAIProvider):
    """
    OpenAI Cloud LLM Provider (gpt-4o-mini).
    Communicates securely with OpenAI Chat Completions API.
    """
    def __init__(self, api_key=None):
        super().__init__(
            provider_code="gpt-4o-mini",
            display_name="OpenAI (gpt-4o-mini)",
            is_online=True
        )
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", OPENAI_API_KEY)

    def check_availability(self):
        key = os.environ.get("OPENAI_API_KEY", self.api_key)
        if not key or len(key) < 8 or key.startswith("sk-fake"):
            return False, "OpenAI API key is not configured or is a placeholder."
        return True, "OpenAI API key is configured and ready for live cloud inference."

    def generate_test_cases(self, title, description, module_name, acceptance_criteria, test_types):
        key = os.environ.get("OPENAI_API_KEY", self.api_key)
        if not key or len(key) < 8 or key.startswith("sk-fake"):
            return None, "OpenAI API key is not configured."

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        prompt = f"""You are a Principal Software QA Automation Architect.
Generate structured QA test cases for:
Title: {title} | Module: {module_name}
Description: {description}
Acceptance Criteria: {acceptance_criteria}
Test Types: {', '.join(test_types)}

Return ONLY a JSON array with objects matching: title, test_type, priority, gherkin_text, pre_conditions, steps_json, expected_result.
Allowed actions: navigate, click, input, clear, assert_text, assert_visible, assert_not_visible, assert_count_gt, assert_disabled."""

        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                raw_text = data['choices'][0]['message']['content']
                parsed = json.loads(raw_text)
                test_cases = parsed if isinstance(parsed, list) else parsed.get("test_cases", parsed.get("cases", []))
                return test_cases, None
            elif res.status_code == 429:
                return None, "OpenAI rate limit exceeded (HTTP 429)."
            elif res.status_code in (401, 403):
                return None, f"OpenAI authentication failed (HTTP {res.status_code})."
            else:
                return None, f"OpenAI returned HTTP {res.status_code}"
        except requests.exceptions.Timeout:
            return None, "OpenAI request timed out after 10s."
        except Exception as e:
            return None, f"OpenAI request error: {str(e)}"

    def analyze_failure_rca(self, test_title, error_message, stack_trace="", browser_logs=""):
        key = os.environ.get("OPENAI_API_KEY", self.api_key)
        if not key or len(key) < 8 or key.startswith("sk-fake"):
            return None, "OpenAI API key is not configured."

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        prompt = f"""Perform Root Cause Analysis for QA Failure:
Title: {test_title}
Error: {error_message}
Stack: {stack_trace}
Logs: {browser_logs}

Return JSON with: title, severity, module, summary, steps_to_reproduce, actual_result, expected_result, root_cause_analysis, ai_fix_suggestion."""

        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return json.loads(data['choices'][0]['message']['content']), None
            return None, f"OpenAI error (HTTP {res.status_code})"
        except Exception as e:
            return None, f"OpenAI error: {str(e)}"

    def chat(self, user_message, history=None):
        key = os.environ.get("OPENAI_API_KEY", self.api_key)
        if not key or len(key) < 8 or key.startswith("sk-fake"):
            return None, "OpenAI API key is not configured."

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are the AI QA Assistant Copilot, specialized in test automation and QA engineering."},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.4
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return {
                    "reply": data['choices'][0]['message']['content'],
                    "provider": self.provider_code,
                    "display_name": self.display_name,
                    "is_online": True
                }, None
            return None, f"OpenAI chat failed (HTTP {res.status_code})"
        except Exception as e:
            return None, f"OpenAI chat error: {str(e)}"


import time
import threading
from collections import deque

class AIAssistantEngine:
    """
    Central AI Copilot Engine coordinating Online LLMs and Offline Heuristics.
    Enforces strict schema validation, action allowlists, provider transparency, and safe fallbacks.
    Tracks real generation latency without fabricating numbers.
    """
    def __init__(self):
        self.heuristic_provider = OfflineHeuristicProvider()
        self.gemini_provider = GeminiLLMProvider()
        self.openai_provider = OpenAILLMProvider()

        # Read fallback policy from config (can be overridden by env at runtime)
        self.fallback_enabled = AI_FALLBACK_ENABLED

        # Thread-safe sliding window for genuine latency measurements
        self._latency_samples = deque(maxlen=30)
        self._latency_lock = threading.Lock()

        # Full telemetry for the most recent generation call
        self.last_generation_info = {
            "provider_used": "offline-heuristic",
            "model": "Heuristic BDD Rule-Engine v2.4",
            "is_fallback": False,
            "fallback_used": False,
            "fallback_reason": None,
            "latency_ms": None,
            "status": "IDLE",
            "timestamp": None,
        }

    def _record_latency(self, latency_ms, provider_code):
        with self._latency_lock:
            self._latency_samples.append({
                "latency_ms": latency_ms,
                "provider": provider_code,
                "timestamp": time.time()
            })

    def get_average_latency_metrics(self):
        """Calculates true average latency from recorded execution samples."""
        with self._latency_lock:
            samples = list(self._latency_samples)

        if not samples:
            return {
                "latency_ms": None,
                "latency_display": "Not measured",
                "samples_count": 0,
                "time_window": "Last 30 generation requests"
            }

        latencies = [s["latency_ms"] for s in samples if s["latency_ms"] is not None]
        if not latencies:
            return {
                "latency_ms": None,
                "latency_display": "Not measured",
                "samples_count": 0,
                "time_window": "Last 30 generation requests"
            }

        avg = round(sum(latencies) / len(latencies), 1)
        return {
            "latency_ms": avg,
            "latency_display": f"{avg} ms ({len(latencies)} sample{'s' if len(latencies) > 1 else ''})",
            "samples_count": len(latencies),
            "time_window": f"Sliding window of last {len(latencies)} requests"
        }

    def _get_fallback_enabled(self):
        """Reads AI_FALLBACK_ENABLED from environment at call-time (supports test monkeypatching)."""
        return os.environ.get("AI_FALLBACK_ENABLED", "true").lower() in ("1", "true", "yes")

    def _get_preferred_online_provider(self):
        pref = os.environ.get("AI_PROVIDER", AI_PROVIDER).lower()
        if pref == "openai":
            is_avail, _ = self.openai_provider.check_availability()
            return self.openai_provider if is_avail else None
        elif pref == "gemini":
            is_avail, _ = self.gemini_provider.check_availability()
            return self.gemini_provider if is_avail else None
        elif pref in ("hybrid", "auto"):
            is_avail_g, _ = self.gemini_provider.check_availability()
            if is_avail_g:
                return self.gemini_provider
            is_avail_o, _ = self.openai_provider.check_availability()
            if is_avail_o:
                return self.openai_provider
        return None

    def get_engine_status(self):
        """
        Returns transparent health and capability metrics for the AI Copilot.

        Dashboard label semantics (dashboard_label field):
          "ONLINE — Gemini AI"                          → Gemini key valid, last call succeeded
          "FALLBACK — Offline Heuristic"                → Gemini tried but failed; heuristic used
          "UNAVAILABLE — Gemini unavailable" → No valid GEMINI_API_KEY present
        """
        online_provider = self._get_preferred_online_provider()
        latency_info = self.get_average_latency_metrics()
        configured_provider = os.environ.get("AI_PROVIDER", AI_PROVIDER).lower()

        capabilities = [
            {"name": "BDD Scenario Generation (Gherkin)", "status": "Implemented & Active", "type": "Core"},
            {"name": "Root Cause Analysis (RCA)", "status": "Implemented & Active", "type": "Core"},
            {"name": "Requirement Impact Analysis", "status": "Implemented & Active", "type": "Core"},
            {"name": "Traceability Matrix Mapping", "status": "Implemented & Active", "type": "Core"}
        ]

        if online_provider:
            # Determine dashboard label based on last generation outcome
            last_was_fallback = self.last_generation_info.get("fallback_used", False)
            if last_was_fallback:
                dashboard_label = GeminiLLMProvider.LABEL_FALLBACK
            else:
                if isinstance(online_provider, GeminiLLMProvider):
                    dashboard_label = GeminiLLMProvider.LABEL_ONLINE
                else:
                    dashboard_label = f"ONLINE — {online_provider.display_name}"

            return {
                "status": "OPERATIONAL",
                "status_text": f"Live LLM Connected ({online_provider.provider_code})",
                "dashboard_label": dashboard_label,
                "active_provider": online_provider.display_name,
                "provider_code": online_provider.provider_code,
                "model_name": online_provider.provider_code,
                "mode": "ONLINE_CLOUD_LLM",
                "is_online": True,
                "is_fallback": False,
                "warning": None,
                "trust_level": f"Generative Cloud LLM ({online_provider.provider_code})",
                "latency_ms": latency_info["latency_ms"],
                "latency_display": latency_info["latency_display"],
                "latency_samples_count": latency_info["samples_count"],
                "badge_class": "badge-ai-online",
                "details": f"Direct cloud inference via {online_provider.display_name} with schema-guided generation.",
                "privacy_statement": (
                    "Requirement titles, descriptions, and acceptance criteria are transmitted "
                    "to the external cloud LLM API over TLS. "
                    "No credentials, tokens, or system passwords are sent."
                ),
                "capabilities": capabilities,
                "last_generation": self.last_generation_info,
            }
        else:
            has_intent_for_online = configured_provider in ("gemini", "openai")

            # Choose the correct dashboard label
            if configured_provider == "gemini":
                gemini_key = os.environ.get("GEMINI_API_KEY", "")
                if not self.gemini_provider._key_is_valid(gemini_key):
                    dashboard_label = GeminiLLMProvider.LABEL_NO_KEY
                else:
                    dashboard_label = GeminiLLMProvider.LABEL_FALLBACK
            elif has_intent_for_online:
                dashboard_label = GeminiLLMProvider.LABEL_FALLBACK
            else:
                dashboard_label = GeminiLLMProvider.LABEL_FALLBACK

            warning_msg = None
            if has_intent_for_online:
                warning_msg = (
                    f"Configured provider '{configured_provider}' is unavailable "
                    "(missing or invalid API key). Operating via Offline Heuristic Engine."
                )

            return {
                "status": "OPERATIONAL",
                "status_text": "Offline QA Heuristic Engine Active",
                "dashboard_label": dashboard_label,
                "active_provider": self.heuristic_provider.display_name,
                "provider_code": self.heuristic_provider.provider_code,
                "model_name": "Heuristic BDD Rule-Engine v2.4",
                "mode": "OFFLINE_FALLBACK",
                "is_online": False,
                "is_fallback": True,
                "warning": warning_msg,
                "trust_level": "Offline Heuristic (Zero External Transmission)",
                "latency_ms": latency_info["latency_ms"],
                "latency_display": latency_info["latency_display"],
                "latency_samples_count": latency_info["samples_count"],
                "badge_class": "badge-ai-fallback",
                "details": (
                    "Operating with deterministic rule-based QA heuristics and BDD templates. "
                    "Zero external API dependencies or network transmission."
                ),
                "privacy_statement": (
                    "All test scenario synthesis and RCA diagnostics occur entirely locally "
                    "in-memory. No data is sent to external third-party services."
                ),
                "capabilities": capabilities,
                "last_generation": self.last_generation_info,
            }

    def generate_test_cases(self, title, description, module_name, acceptance_criteria="", test_types=None):
        """
        Generates structured QA test cases with schema validation and provider transparency.

        Execution flow:
          1. If an online provider is available, attempt live LLM generation.
          2. Validate the schema and action allowlist of the returned test cases.
          3. If validation passes → return online results with full telemetry.
          4. If validation fails OR provider errors → check AI_FALLBACK_ENABLED.
          5. If fallback enabled → run Offline Heuristic Engine and stamp fallback_used=True.
          6. If fallback disabled → return error without heuristic substitution.

        Telemetry fields in last_generation_info:
          provider_used  : code of the provider that produced the final output
          model          : human-readable model name
          latency_ms     : wall-clock ms (perf_counter) of the successful request
          fallback_used  : True only when heuristic substituted for an online provider
          fallback_reason: error text that caused the fallback
          status         : SUCCESS | FALLBACK | NO_PROVIDER | ERROR
          timestamp      : time.time() of completion
        """
        if test_types is None:
            test_types = ["Functional", "Negative", "Boundary", "Security"]

        start_time = time.perf_counter()
        online_provider = self._get_preferred_online_provider()
        fallback_reason = None
        fallback_enabled = self._get_fallback_enabled()

        if online_provider:
            try:
                raw_cases, err = online_provider.generate_test_cases(
                    title=title,
                    description=description,
                    module_name=module_name,
                    acceptance_criteria=acceptance_criteria,
                    test_types=test_types,
                )
                duration_ms = round((time.perf_counter() - start_time) * 1000, 1)

                if not err and raw_cases and self._validate_test_cases_schema(raw_cases):
                    # ── Successful online generation ───────────────────────
                    for tc in raw_cases:
                        tc["provider"] = online_provider.provider_code
                    self._record_latency(duration_ms, online_provider.provider_code)
                    self.last_generation_info = {
                        "provider_used": online_provider.provider_code,
                        "model": online_provider.provider_code,
                        "is_fallback": False,
                        "fallback_used": False,
                        "fallback_reason": None,
                        "latency_ms": duration_ms,
                        "status": "SUCCESS",
                        "timestamp": time.time(),
                    }
                    return raw_cases, online_provider.provider_code
                else:
                    fallback_reason = err or "Online LLM output failed schema or action validation."
                    print(f"[AI Engine] Online generation failed: {fallback_reason}")
            except Exception as exc:
                fallback_reason = f"Online provider exception: {str(exc)}"
                print(f"[AI Engine] Online provider exception: {fallback_reason}")

        # ── Fallback decision ──────────────────────────────────────────────
        if not fallback_enabled and online_provider and fallback_reason:
            # Caller explicitly disabled fallback — surface the error.
            self.last_generation_info = {
                "provider_used": online_provider.provider_code,
                "model": online_provider.provider_code,
                "is_fallback": False,
                "fallback_used": False,
                "fallback_reason": fallback_reason,
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
                "status": "ERROR",
                "timestamp": time.time(),
            }
            return [], online_provider.provider_code

        # ── Offline Heuristic Fallback ─────────────────────────────────────
        h_start = time.perf_counter()
        heuristic_cases, _ = self.heuristic_provider.generate_test_cases(
            title=title,
            description=description,
            module_name=module_name,
            acceptance_criteria=acceptance_criteria,
            test_types=test_types,
        )
        duration_ms = round((time.perf_counter() - h_start) * 1000, 1)

        for tc in heuristic_cases:
            tc["provider"] = self.heuristic_provider.provider_code

        self._record_latency(duration_ms, self.heuristic_provider.provider_code)
        self.last_generation_info = {
            "provider_used": self.heuristic_provider.provider_code,
            "model": "Heuristic BDD Rule-Engine v2.4",
            "is_fallback": bool(online_provider is not None),
            "fallback_used": bool(online_provider is not None),
            "fallback_reason": fallback_reason,
            "latency_ms": duration_ms,
            "status": "FALLBACK" if online_provider else "NO_PROVIDER",
            "timestamp": time.time(),
        }
        return heuristic_cases, self.heuristic_provider.provider_code

    def _validate_test_cases_schema(self, cases):
        """Validates that all generated test cases satisfy the required schema and allowed actions."""
        if not isinstance(cases, list) or len(cases) == 0:
            return False

        for c in cases:
            if not isinstance(c, dict):
                return False
            if not REQUIRED_TC_FIELDS.issubset(c.keys()):
                return False
            if c.get("test_type") not in ALLOWED_TEST_TYPES:
                c["test_type"] = "Functional"

            steps = c.get("steps_json", [])
            if not isinstance(steps, list):
                return False

            for step in steps:
                if not isinstance(step, dict):
                    return False
                action = str(step.get("action", "")).lower().strip()
                if action not in VALID_ACTIONS:
                    return False

        return True

    def analyze_failure_and_generate_bug_report(self, test_title, error_message, stack_trace="", browser_logs=""):
        """Performs AI Root Cause Analysis (RCA) and defect synthesis with safe fallback."""
        start_time = time.perf_counter()
        online_provider = self._get_preferred_online_provider()

        if online_provider:
            try:
                rca, err = online_provider.analyze_failure_rca(
                    test_title=test_title,
                    error_message=error_message,
                    stack_trace=stack_trace,
                    browser_logs=browser_logs
                )
                duration_ms = round((time.perf_counter() - start_time) * 1000, 1)
                if not err and rca and isinstance(rca, dict) and "root_cause_analysis" in rca:
                    self._record_latency(duration_ms, online_provider.provider_code)
                    return rca
            except Exception as e:
                print(f"[AI Engine RCA] Fallback to heuristic RCA due to: {e}")

        # Fallback to heuristic RCA
        h_start = time.perf_counter()
        rca, _ = self.heuristic_provider.analyze_failure_rca(
            test_title=test_title,
            error_message=error_message,
            stack_trace=stack_trace,
            browser_logs=browser_logs
        )
        duration_ms = round((time.perf_counter() - h_start) * 1000, 1)
        self._record_latency(duration_ms, self.heuristic_provider.provider_code)
        return rca

    def chat_with_copilot(self, user_message, context=None):
        """Processes conversational QA queries with live LLM or offline heuristics."""
        start_time = time.perf_counter()
        online_provider = self._get_preferred_online_provider()

        if online_provider:
            try:
                reply_dict, err = online_provider.chat(user_message)
                duration_ms = round((time.perf_counter() - start_time) * 1000, 1)
                if not err and reply_dict and "reply" in reply_dict:
                    self._record_latency(duration_ms, online_provider.provider_code)
                    return reply_dict
            except Exception as e:
                print(f"[AI Copilot Chat] Fallback to heuristic chat due to: {e}")

        h_start = time.perf_counter()
        reply_dict, _ = self.heuristic_provider.chat(user_message)
        duration_ms = round((time.perf_counter() - h_start) * 1000, 1)
        self._record_latency(duration_ms, self.heuristic_provider.provider_code)
        return reply_dict


ai_engine = AIAssistantEngine()

