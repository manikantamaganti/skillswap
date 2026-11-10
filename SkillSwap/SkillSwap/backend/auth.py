"""
Authentication, Session Management & User Profile Routes for SkillSwap
Supports Role-Based Access (Student / Admin)
"""

import re
from functools import wraps
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import execute_query

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Please log in to continue."}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            return jsonify({"success": False, "message": "Admin privileges required."}), 403
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    college_name = data.get("college_name", "").strip()
    department = data.get("department", "").strip()
    year_of_study = data.get("year_of_study", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    profile_image = data.get("profile_image", "default_avatar.png").strip() or "default_avatar.png"

    # Validations
    if not all([full_name, email, college_name, department, year_of_study, password]):
        return jsonify({"success": False, "message": "All required fields must be completed."}), 400

    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, email):
        return jsonify({"success": False, "message": "Please enter a valid email address."}), 400

    if password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match."}), 400

    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters long."}), 400

    # Check duplicate email
    existing = execute_query(
        "SELECT user_id FROM users WHERE email = %s;",
        (email,),
        fetchone=True
    )
    if existing:
        return jsonify({"success": False, "message": "An account with this email already exists."}), 409

    password_hash = generate_password_hash(password)
    default_bio = f"Hello! I am a {year_of_study} student in {department} at {college_name}. Excited to swap skills on SkillSwap."

    user_id = execute_query(
        """
        INSERT INTO users (full_name, email, password_hash, college_name, department, year_of_study, bio, profile_image, role, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'student', 'active');
        """,
        (full_name, email, password_hash, college_name, department, year_of_study, default_bio, profile_image),
        commit=True
    )

    # Create welcome notification
    execute_query(
        """
        INSERT INTO notifications (user_id, title, message, type, link)
        VALUES (%s, 'Welcome to SkillSwap!', 'Start by adding your teaching skills and learning goals on the Skills page.', 'system', 'skills.html');
        """,
        (user_id,),
        commit=True
    )

    return jsonify({
        "success": True,
        "message": "Registration successful! You can now log in.",
        "user_id": user_id
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    remember_me = bool(data.get("remember_me", False))

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    user = execute_query(
        """
        SELECT user_id, full_name, email, password_hash, college_name, department, 
               year_of_study, bio, profile_image, role, status
        FROM users WHERE email = %s;
        """,
        (email,),
        fetchone=True
    )

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    if user["status"] == "suspended":
        return jsonify({"success": False, "message": "Your account has been suspended by an administrator."}), 403

    session["user_id"] = user["user_id"]
    session["role"] = user["role"]
    session["full_name"] = user["full_name"]
    session.permanent = remember_me

    safe_user = {k: v for k, v in user.items() if k != "password_hash"}

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user['full_name']}!",
        "user": safe_user
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."}), 200


@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "authenticated": False, "message": "Not logged in."}), 401

    user = execute_query(
        """
        SELECT user_id, full_name, email, college_name, department, 
               year_of_study, bio, profile_image, role, status, created_at
        FROM users WHERE user_id = %s;
        """,
        (user_id,),
        fetchone=True
    )

    if not user:
        session.clear()
        return jsonify({"success": False, "authenticated": False, "message": "User not found."}), 404

    # Fetch teaching skills
    teaching = execute_query(
        """
        SELECT s.skill_id, s.skill_name, s.category
        FROM student_skills ss
        JOIN skills s ON ss.skill_id = s.skill_id
        WHERE ss.user_id = %s AND ss.skill_type = 'teach'
        ORDER BY s.skill_name;
        """,
        (user_id,),
        fetchall=True
    ) or []

    # Fetch learning skills
    learning = execute_query(
        """
        SELECT s.skill_id, s.skill_name, s.category
        FROM student_skills ss
        JOIN skills s ON ss.skill_id = s.skill_id
        WHERE ss.user_id = %s AND ss.skill_type = 'learn'
        ORDER BY s.skill_name;
        """,
        (user_id,),
        fetchall=True
    ) or []

    # Unread notifications count
    unread_notifs = execute_query(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = 0;",
        (user_id,),
        fetchone=True
    )
    unread_count = int(unread_notifs["cnt"]) if unread_notifs else 0

    # Total connections
    conns = execute_query(
        "SELECT COUNT(*) AS cnt FROM connections WHERE user1_id = %s OR user2_id = %s;",
        (user_id, user_id),
        fetchone=True
    )
    total_connections = int(conns["cnt"]) if conns else 0

    user["teaching_skills"] = teaching
    user["learning_skills"] = learning
    user["unread_notifications"] = unread_count
    user["total_connections"] = total_connections

    return jsonify({
        "success": True,
        "authenticated": True,
        "user": user
    }), 200


@auth_bp.route("/profile", methods=["PUT"])
@login_required
def update_profile():
    user_id = session.get("user_id")
    data = request.get_json() or {}

    full_name = data.get("full_name", "").strip()
    college_name = data.get("college_name", "").strip()
    department = data.get("department", "").strip()
    year_of_study = data.get("year_of_study", "").strip()
    bio = data.get("bio", "").strip()
    profile_image = data.get("profile_image", "").strip()

    if not full_name or not college_name or not department or not year_of_study:
        return jsonify({"success": False, "message": "Name, college, department, and year are required."}), 400

    if profile_image:
        execute_query(
            """
            UPDATE users 
            SET full_name = %s, college_name = %s, department = %s, 
                year_of_study = %s, bio = %s, profile_image = %s
            WHERE user_id = %s;
            """,
            (full_name, college_name, department, year_of_study, bio, profile_image, user_id),
            commit=True
        )
    else:
        execute_query(
            """
            UPDATE users 
            SET full_name = %s, college_name = %s, department = %s, 
                year_of_study = %s, bio = %s
            WHERE user_id = %s;
            """,
            (full_name, college_name, department, year_of_study, bio, user_id),
            commit=True
        )

    session["full_name"] = full_name

    return jsonify({
        "success": True,
        "message": "Profile updated successfully!"
    }), 200

