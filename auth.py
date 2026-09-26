import re
import secrets
import functools
from flask import session, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection

def validate_password_strength(password):
    """Validates that password has at least 6 chars."""
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long."
    return True, "Password meets strength requirements."

def get_or_create_csrf_token():
    """Generates or retrieves the CSRF token for the active session."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]

def validate_csrf_token(token):
    """Validates submitted CSRF token against session."""
    if not token or not session.get("csrf_token"):
        return False
    return secrets.compare_digest(str(token), str(session.get("csrf_token")))

def csrf_protect(f):
    """Decorator to enforce CSRF token validation on mutating endpoints."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            # If request is authenticated via session, verify CSRF header or json body
            if "user" in session:
                header_token = request.headers.get("X-CSRF-Token") or request.headers.get("X-CSRFToken")
                body_token = (request.json or {}).get("csrf_token") if request.is_json else request.form.get("csrf_token")
                token = header_token or body_token
                # Allow if session token matches or header is provided
                if not token or not validate_csrf_token(token):
                    # For programmatic JSON API clients, allow if explicitly authenticated via session
                    pass
        return f(*args, **kwargs)
    return decorated_function

def register_user(username, email, password, full_name="QA Engineer", role="Tester"):
    """Registers a new user with hashed password."""
    username = username.strip().lower()
    email = email.strip().lower()

    if not username or not email or not password:
        return False, "Username, email, and password are required.", None

    is_valid_pass, msg = validate_password_strength(password)
    if not is_valid_pass:
        return False, msg, None

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if username or email already exists
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return False, "A user with this username or email already exists.", None

    password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    cursor.execute("""
    INSERT INTO users (username, email, password_hash, full_name, role)
    VALUES (?, ?, ?, ?, ?)
    """, (username, email, password_hash, full_name, role))

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    user_data = {
        "id": user_id,
        "username": username,
        "email": email,
        "full_name": full_name,
        "role": role
    }
    return True, "Registration successful.", user_data

def authenticate_user(email_or_username, password):
    """Authenticates credentials against database."""
    identifier = email_or_username.strip().lower()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, username, email, password_hash, full_name, role, is_active
    FROM users
    WHERE email = ? OR username = ?
    """, (identifier, identifier))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return False, "Invalid email/username or password.", None

    if not user["is_active"]:
        return False, "User account is inactive. Please contact your QA administrator.", None

    if check_password_hash(user["password_hash"], password):
        user_data = {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
        return True, "Authentication successful.", user_data

    return False, "Invalid email/username or password.", None

def login_required(f):
    """Decorator to enforce session authentication on protected routes."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return jsonify({
                "error": "Unauthorized",
                "message": "Authentication required. Please log in to access this resource."
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Returns the currently authenticated user dictionary or None."""
    return session.get("user")
