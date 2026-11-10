"""
Learning Sessions Management for SkillSwap
Allows connected peers to schedule, coordinate, and complete peer study meetings.
"""

from flask import Blueprint, request, jsonify, session
from database import execute_query
from auth import login_required
from chat import are_students_connected

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/sessions")


@sessions_bp.route("", methods=["GET"])
@login_required
def get_user_sessions():
    user_id = session.get("user_id")

    sessions_list = execute_query(
        """
        SELECT ls.session_id, ls.host_id, ls.partner_id, ls.session_title, 
               ls.skill_name, ls.session_date, ls.session_time, ls.description, 
               ls.meeting_link, ls.status, ls.created_at,
               u1.full_name AS host_name, u1.profile_image AS host_avatar,
               u2.full_name AS partner_name, u2.profile_image AS partner_avatar
        FROM learning_sessions ls
        JOIN users u1 ON ls.host_id = u1.user_id
        JOIN users u2 ON ls.partner_id = u2.user_id
        WHERE ls.host_id = %s OR ls.partner_id = %s
        ORDER BY ls.session_date ASC, ls.session_time ASC;
        """,
        (user_id, user_id),
        fetchall=True
    ) or []

    upcoming = [s for s in sessions_list if s["status"] == "upcoming"]
    past = [s for s in sessions_list if s["status"] != "upcoming"]

    return jsonify({
        "success": True,
        "upcoming": upcoming,
        "past": past,
        "all": sessions_list
    }), 200


@sessions_bp.route("", methods=["POST"])
@login_required
def create_session():
    host_id = session.get("user_id")
    host_name = session.get("full_name", "Your Peer")
    data = request.get_json() or {}

    partner_id = data.get("partner_id")
    session_title = data.get("session_title", "").strip()
    skill_name = data.get("skill_name", "").strip()
    session_date = data.get("session_date", "").strip()
    session_time = data.get("session_time", "").strip()
    description = data.get("description", "").strip()
    meeting_link = data.get("meeting_link", "").strip()

    if not all([partner_id, session_title, skill_name, session_date, session_time]):
        return jsonify({"success": False, "message": "Partner, Title, Skill, Date, and Time are required."}), 400

    try:
        partner_id = int(partner_id)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid partner ID."}), 400

    if not are_students_connected(host_id, partner_id):
        return jsonify({"success": False, "message": "You can only schedule learning sessions with connected students."}), 403

    session_id = execute_query(
        """
        INSERT INTO learning_sessions 
        (host_id, partner_id, session_title, skill_name, session_date, session_time, description, meeting_link, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'upcoming');
        """,
        (host_id, partner_id, session_title, skill_name, session_date, session_time, description, meeting_link),
        commit=True
    )

    # Notify Partner
    execute_query(
        """
        INSERT INTO notifications (user_id, title, message, type, link)
        VALUES (%s, 'New Learning Session Scheduled 📅', %s, 'session', 'sessions.html');
        """,
        (partner_id, f"{host_name} scheduled a session: '{session_title}' ({skill_name}) for {session_date} at {session_time}."),
        commit=True
    )

    return jsonify({
        "success": True,
        "message": "Learning session successfully scheduled!",
        "session_id": session_id
    }), 201


@sessions_bp.route("/<int:session_id>/status", methods=["PUT"])
@login_required
def update_session_status(session_id):
    user_id = session.get("user_id")
    data = request.get_json() or {}
    new_status = data.get("status", "").strip().lower()

    if new_status not in ["completed", "cancelled"]:
        return jsonify({"success": False, "message": "Status must be 'completed' or 'cancelled'."}), 400

    sess = execute_query(
        "SELECT * FROM learning_sessions WHERE session_id = %s;",
        (session_id,),
        fetchone=True
    )
    if not sess:
        return jsonify({"success": False, "message": "Session not found."}), 404

    if user_id not in (sess["host_id"], sess["partner_id"]):
        return jsonify({"success": False, "message": "You are not a participant in this session."}), 403

    execute_query(
        "UPDATE learning_sessions SET status = %s WHERE session_id = %s;",
        (new_status, session_id),
        commit=True
    )

    other_user = sess["partner_id"] if user_id == sess["host_id"] else sess["host_id"]
    execute_query(
        """
        INSERT INTO notifications (user_id, title, message, type, link)
        VALUES (%s, %s, %s, 'session', 'sessions.html');
        """,
        (other_user, f"Session Status Update: {new_status.title()}", f"The session '{sess['session_title']}' has been marked as {new_status}."),
        commit=True
    )

    return jsonify({"success": True, "message": f"Session marked as {new_status}.", "status": new_status}), 200

