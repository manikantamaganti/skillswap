"""
Admin Dashboard & Platform Management Module for SkillSwap
Provides role-protected oversight of students, skills, requests, and activity metrics.
"""

from flask import Blueprint, request, jsonify, session
from database import execute_query
from auth import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/stats", methods=["GET"])
@admin_required
def get_admin_stats():
    total_students = execute_query(
        "SELECT COUNT(*) AS cnt FROM users WHERE role = 'student';",
        fetchone=True
    )["cnt"]

    total_skills = execute_query(
        "SELECT COUNT(*) AS cnt FROM skills;",
        fetchone=True
    )["cnt"]

    total_requests = execute_query(
        "SELECT COUNT(*) AS cnt FROM skill_exchange_requests;",
        fetchone=True
    )["cnt"]

    active_sessions = execute_query(
        "SELECT COUNT(*) AS cnt FROM learning_sessions WHERE status = 'upcoming';",
        fetchone=True
    )["cnt"]

    total_connections = execute_query(
        "SELECT COUNT(*) AS cnt FROM connections;",
        fetchone=True
    )["cnt"]

    total_messages = execute_query(
        "SELECT COUNT(*) AS cnt FROM messages;",
        fetchone=True
    )["cnt"]

    return jsonify({
        "success": True,
        "stats": {
            "total_students": total_students,
            "total_skills": total_skills,
            "total_requests": total_requests,
            "active_sessions": active_sessions,
            "total_connections": total_connections,
            "total_messages": total_messages
        }
    }), 200


@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_all_users():
    users = execute_query(
        """
        SELECT u.user_id, u.full_name, u.email, u.college_name, u.department, 
               u.year_of_study, u.role, u.status, u.created_at,
               (SELECT COUNT(*) FROM student_skills ss WHERE ss.user_id = u.user_id AND ss.skill_type = 'teach') AS teach_count,
               (SELECT COUNT(*) FROM student_skills ss WHERE ss.user_id = u.user_id AND ss.skill_type = 'learn') AS learn_count,
               (SELECT COUNT(*) FROM skill_exchange_requests sr WHERE sr.sender_id = u.user_id OR sr.receiver_id = u.user_id) AS request_count
        FROM users u
        WHERE u.role = 'student'
        ORDER BY u.created_at DESC;
        """,
        fetchall=True
    ) or []

    return jsonify({"success": True, "users": users}), 200


@admin_bp.route("/users/<int:user_id>/status", methods=["PUT"])
@admin_required
def toggle_user_status(user_id):
    data = request.get_json() or {}
    new_status = data.get("status", "").strip().lower()

    if new_status not in ["active", "suspended"]:
        return jsonify({"success": False, "message": "Status must be 'active' or 'suspended'."}), 400

    execute_query(
        "UPDATE users SET status = %s WHERE user_id = %s AND role != 'admin';",
        (new_status, user_id),
        commit=True
    )

    return jsonify({"success": True, "message": f"Student status updated to '{new_status}'."}), 200


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    deleted = execute_query(
        "DELETE FROM users WHERE user_id = %s AND role != 'admin';",
        (user_id,),
        commit=True
    )
    if deleted:
        return jsonify({"success": True, "message": "Student account removed from platform."}), 200
    return jsonify({"success": False, "message": "Cannot delete admin or user not found."}), 400


@admin_bp.route("/skills", methods=["POST"])
@admin_required
def add_skill():
    data = request.get_json() or {}
    skill_name = data.get("skill_name", "").strip()
    category = data.get("category", "General").strip() or "General"

    if not skill_name:
        return jsonify({"success": False, "message": "Skill name is required."}), 400

    existing = execute_query(
        "SELECT skill_id FROM skills WHERE LOWER(skill_name) = LOWER(%s);",
        (skill_name,),
        fetchone=True
    )
    if existing:
        return jsonify({"success": False, "message": "Skill already exists."}), 409

    skill_id = execute_query(
        "INSERT INTO skills (skill_name, category) VALUES (%s, %s);",
        (skill_name, category),
        commit=True
    )
    return jsonify({"success": True, "message": f"Skill '{skill_name}' added to catalog.", "skill_id": skill_id}), 201


@admin_bp.route("/skills/<int:skill_id>", methods=["DELETE"])
@admin_required
def delete_skill(skill_id):
    execute_query("DELETE FROM skills WHERE skill_id = %s;", (skill_id,), commit=True)
    return jsonify({"success": True, "message": "Skill deleted from catalog."}), 200


@admin_bp.route("/activity", methods=["GET"])
@admin_required
def get_platform_activity():
    recent_requests = execute_query(
        """
        SELECT r.request_id, r.skill_offered, r.skill_requested, r.status, r.created_at,
               u1.full_name AS sender_name, u2.full_name AS receiver_name
        FROM skill_exchange_requests r
        JOIN users u1 ON r.sender_id = u1.user_id
        JOIN users u2 ON r.receiver_id = u2.user_id
        ORDER BY r.created_at DESC LIMIT 10;
        """,
        fetchall=True
    ) or []

    recent_sessions = execute_query(
        """
        SELECT ls.session_id, ls.session_title, ls.skill_name, ls.session_date, ls.status,
               u1.full_name AS host_name, u2.full_name AS partner_name
        FROM learning_sessions ls
        JOIN users u1 ON ls.host_id = u1.user_id
        JOIN users u2 ON ls.partner_id = u2.user_id
        ORDER BY ls.created_at DESC LIMIT 10;
        """,
        fetchall=True
    ) or []

    return jsonify({
        "success": True,
        "recent_requests": recent_requests,
        "recent_sessions": recent_sessions
    }), 200

