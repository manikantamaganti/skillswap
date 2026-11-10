"""
Main Application Factory & Central REST API Gateway for SkillSwap
A Student Skill Enhancement and Peer Learning Platform
"""

import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, session
from flask_cors import CORS

from database import init_db, execute_query
from auth import auth_bp, login_required
from skills import skills_bp
from matching import matching_bp
from requests import requests_bp
from chat import chat_bp
from sessions import sessions_bp
from admin import admin_bp

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOADS_DIR = BASE_DIR / "uploads"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", "skillswap-secure-token-key-2026-cse-project")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

# Enable CORS with credentials
CORS(app, supports_credentials=True, origins=[
    "http://127.0.0.1:5000", "http://localhost:5000",
    "http://127.0.0.1:5500", "http://localhost:3000", "null"
])

# Register modular blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(skills_bp)
app.register_blueprint(matching_bp)
app.register_blueprint(requests_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(admin_bp)


# ========================================================
# Dashboard Aggregate Endpoint
# ========================================================
@app.route("/api/dashboard", methods=["GET"])
@login_required
def get_dashboard_data():
    user_id = session.get("user_id")

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
        return jsonify({"success": False, "message": "User not found."}), 404

    # Teaching skills
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

    # Learning skills
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

    # Counts
    pending_reqs = execute_query(
        "SELECT COUNT(*) AS cnt FROM skill_exchange_requests WHERE receiver_id = %s AND status = 'pending';",
        (user_id,),
        fetchone=True
    )["cnt"]

    conns = execute_query(
        "SELECT COUNT(*) AS cnt FROM connections WHERE user1_id = %s OR user2_id = %s;",
        (user_id, user_id),
        fetchone=True
    )["cnt"]

    active_sess = execute_query(
        "SELECT COUNT(*) AS cnt FROM learning_sessions WHERE (host_id = %s OR partner_id = %s) AND status = 'upcoming';",
        (user_id, user_id),
        fetchone=True
    )["cnt"]

    # Upcoming sessions snapshot
    upcoming_sessions = execute_query(
        """
        SELECT ls.session_id, ls.session_title, ls.skill_name, ls.session_date, 
               ls.session_time, ls.meeting_link,
               u.full_name AS partner_name, u.profile_image AS partner_avatar
        FROM learning_sessions ls
        JOIN users u ON (CASE WHEN ls.host_id = %s THEN ls.partner_id ELSE ls.host_id END) = u.user_id
        WHERE (ls.host_id = %s OR ls.partner_id = %s) AND ls.status = 'upcoming'
        ORDER BY ls.session_date ASC, ls.session_time ASC
        LIMIT 3;
        """,
        (user_id, user_id, user_id),
        fetchall=True
    ) or []

    # Recent notifications / activities
    notifications = execute_query(
        "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT 5;",
        (user_id,),
        fetchall=True
    ) or []

    unread_count = execute_query(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = 0;",
        (user_id,),
        fetchone=True
    )["cnt"]

    return jsonify({
        "success": True,
        "user": user,
        "stats": {
            "teaching_count": len(teaching),
            "learning_count": len(learning),
            "total_connections": conns,
            "pending_requests": pending_reqs,
            "active_sessions": active_sess,
            "unread_notifications": unread_count
        },
        "teaching_skills": teaching,
        "learning_skills": learning,
        "upcoming_sessions": upcoming_sessions,
        "recent_notifications": notifications
    }), 200


# ========================================================
# Notifications Endpoints
# ========================================================
@app.route("/api/notifications", methods=["GET"])
@login_required
def get_user_notifications():
    user_id = session.get("user_id")
    notifs = execute_query(
        "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC;",
        (user_id,),
        fetchall=True
    ) or []
    return jsonify({"success": True, "notifications": notifs}), 200


@app.route("/api/notifications/mark-read", methods=["PUT"])
@login_required
def mark_notifications_read():
    user_id = session.get("user_id")
    data = request.get_json() or {}
    notif_id = data.get("notification_id")

    if notif_id:
        execute_query("UPDATE notifications SET is_read = 1 WHERE notification_id = %s AND user_id = %s;", (notif_id, user_id), commit=True)
    else:
        execute_query("UPDATE notifications SET is_read = 1 WHERE user_id = %s;", (user_id,), commit=True)

    return jsonify({"success": True, "message": "Notifications marked as read."}), 200


# ========================================================
# Static File & Single/Multi-Page Routing
# ========================================================
@app.route("/")
def serve_index():
    return send_from_directory(str(FRONTEND_DIR), "index.html")


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    if (UPLOADS_DIR / filename).exists():
        return send_from_directory(str(UPLOADS_DIR), filename)
    return send_from_directory(str(FRONTEND_DIR / "uploads"), filename)


@app.route("/<path:path>")
def serve_page(path):
    target = FRONTEND_DIR / path
    if target.exists() and target.is_file():
        return send_from_directory(str(FRONTEND_DIR), path)
    html_target = FRONTEND_DIR / f"{path}.html"
    if html_target.exists():
        return send_from_directory(str(FRONTEND_DIR), f"{path}.html")
    return send_from_directory(str(FRONTEND_DIR), "index.html")


@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "message": "Resource not found."}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "message": "Internal server error."}), 500


if __name__ == "__main__":
    init_db()
    print("\n=======================================================")
    print(" 🚀 SkillSwap Platform Server running!")
    print(" 🌐 Access application at: http://localhost:5000")
    print(" 👤 Demo Student: rahul@college.edu / password123")
    print(" 🛡️ Admin Portal: admin@skillswap.edu / admin123")
    print("=======================================================\n")
    app.run(host="0.0.0.0", port=5000, debug=True)

