import random
import string
import uuid
import datetime

class TestDataFactory:
    """
    Generates synthetic QA test data sets for boundary testing, negative validation,
    security probing, and e-commerce workflows.
    """

    @staticmethod
    def get_email_datasets():
        return {
            "valid": [
                "tester.john@qa-platform.io",
                "sarah.connor+qa@enterprise.com",
                "dev.ops_test@subdomain.example.co.uk",
                "customer10293@mail-service.net",
                "alex.valid@company.org"
            ],
            "invalid_format": [
                "plainaddress_without_at",
                "@missingusername.com",
                "username@.missingdomain",
                "user@domain..com",
                "user with spaces@domain.com",
                "user@domain,com"
            ],
            "boundary_edge_cases": [
                f"{'a'*64}@domain.com",  # Max length username (64 chars)
                f"user@{'b'*60}.com",
                "a@b.co",  # Shortest standard domain
                "user+testing-123_456@test-domain-with-hyphens.org"
            ],
            "security_payloads": [
                "admin' OR '1'='1'--@injection.com",
                "<script>alert('XSS')</script>@test.com",
                "user'; DROP TABLE users;--@hack.com",
                "\"test\\\"user\"@domain.com"
            ]
        }

    @staticmethod
    def get_password_datasets():
        return {
            "valid_strong": [
                "P@ssw0rd2026!",
                "Secure#Vault99!",
                "Alpha_Omega$44",
                "Quantum#Leap_2026!"
            ],
            "weak_boundary": [
                "123456",            # Common numeric
                "password",          # Dictionary word
                "Pass1",             # Short (< 6 chars)
                "        ",          # Only spaces
                "a" * 128            # Max buffer length
            ],
            "special_and_unicode": [
                "Pässwörd123!_ñ",
                "🔒SafeKey2026#",
                "Test'\"`\\/<>|",
                "\t\n\r"
            ]
        }

    @staticmethod
    def get_boundary_numbers():
        return [
            {"label": "Zero (0)", "value": 0, "type": "Boundary Minimum"},
            {"label": "Negative Price (-1.00)", "value": -1.00, "type": "Negative Boundary"},
            {"label": "Minimum Positive (0.01)", "value": 0.01, "type": "Boundary Valid Min"},
            {"label": "Standard Amount (99.99)", "value": 99.99, "type": "Nominal Valid"},
            {"label": "Upper Boundary (99999.99)", "value": 99999.99, "type": "Boundary Valid Max"},
            {"label": "Integer Overflow (2147483648)", "value": 2147483648, "type": "Overflow Boundary"},
            {"label": "Float Precision (0.00000001)", "value": 0.00000001, "type": "Precision Boundary"}
        ]

    @staticmethod
    def get_security_vectors():
        return [
            {"category": "SQL Injection (SQLi)", "payload": "' OR '1'='1' --", "purpose": "Bypass authentication logic"},
            {"category": "SQL Injection (Union)", "payload": "1' UNION SELECT null, username, password FROM users--", "purpose": "Extract sensitive columns"},
            {"category": "Cross-Site Scripting (XSS)", "payload": "<script>alert('QA_XSS_PROBE')</script>", "purpose": "Verify HTML output encoding"},
            {"category": "Image XSS Payload", "payload": "<img src=x onerror=alert('DOM_XSS')>", "purpose": "DOM element injection"},
            {"category": "Command Injection", "payload": "; cat /etc/passwd #", "purpose": "OS command execution verification"},
            {"category": "Path Traversal", "payload": "../../../../windows/win.ini", "purpose": "Unauthorized file access check"}
        ]

    @staticmethod
    def generate_synthetic_profiles(count=5):
        first_names = ["Arun", "Priya", "Vikram", "Sneha", "Rahul", "Ananya", "Rohan", "Kavita"]
        last_names = ["Sharma", "Verma", "Patel", "Mehta", "Singh", "Kumar", "Iyer", "Nair"]
        cities = ["Mumbai", "Bengaluru", "Delhi", "Pune", "Hyderabad", "Chennai"]

        profiles = []
        for i in range(count):
            fn = random.choice(first_names)
            ln = random.choice(last_names)
            city = random.choice(cities)
            phone = f"+91 {random.randint(7000, 9999)} {random.randint(100000, 999999)}"
            email = f"{fn.lower()}.{ln.lower()}{random.randint(10, 99)}@qa-testmail.io"

            profiles.append({
                "id": f"USR-{uuid.uuid4().hex[:6].upper()}",
                "name": f"{fn} {ln}",
                "email": email,
                "phone": phone,
                "address": f"{random.randint(101, 999)}, Tech Park Rd, Sector {random.randint(1, 25)}, {city}",
                "postal_code": f"{random.randint(110001, 600001)}",
                "payment_card": f"4532-****-****-{random.randint(1000, 9999)}",
                "status": "Active"
            })
        return profiles

test_data_factory = TestDataFactory()
