"""
Skill Exchange Request Management & Connections System
Handles proposal sending, status changes (Accept/Reject/Cancel),
automatic peer connection establishment, and notification triggers.
"""

from flask import Blueprint, request, jsonify, session
from database import execute_query
from auth import login_required

requests_bp = Blueprint("requests", __name__, url_prefix="/api/requests")


@requests_bp.route("", methods=["POST"])
@login_required
def send_request():
    sender_id = session.get("user_id")
    sender_name = session.get("full_name", "A peer")
    data = request.get_json() or {}

    receiver_id = data.get("receiver_id")
    skill_offered = data.get("skill_offered", "").strip()
    skill_requested = data.get("skill_requested", "").strip()
    message = data.get("message", "").strip()

    if not receiver_id or not skill_offered or not skill_requested:
        return jsonify({"success": False, "message": "Receiver, skill offered, and skill requested are required."}), 400

    try:
        receiver_id = int(receiver_id)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid receiver ID."}), 400

    if sender_id == receiver_id:
        return jsonify({"success": False, "message": "You cannot send an exchange request to yourself."}), 400

    receiver = execute_query(
        "SELECT user_id, full_name FROM users WHERE user_id = %s;",
        (receiver_id,),
        fetchone=True
    )
    if not receiver:
        return jsonify({"success": False, "message": "Target student does not exist."}), 404

    # Check if already connected
    u1, u2 = min(sender_id, receiver_id), max(sender_id, receiver_id)
    connected = execute_query(
        "SELECT connection_id FROM connections WHERE user1_id = %s AND user2_id = %s;",
        (u1, u2),
        fetchone=True
    )
    if connected:
        return jsonify({"success": False, "message": f"You are already connected with {receiver['full_name']}."}), 409

    # Check duplicate pending request
    duplicate = execute_query(
        """
        SELECT request_id FROM skill_exchange_requests
        WHERE sender_id = %s AND receiver_id = %s AND status = 'pending';
        """,
        (sender_id, receiver_id),
        fetchone=True
    )
    if duplicate:
        return jsonify({"success": False, "message": f"You already have a pending request awaiting {receiver['full_name']}'s response."}), 409

    default_msg = message or f"Hi {receiver['full_name']}! I'd love to exchange my knowledge of {skill_offered} to learn {skill_requested} from you."

    request_id = execute_query(
        """
        INSERT INTO skill_exchange_requests (sender_id, receiver_id, skill_offered, skill_requested, message, status)
        VALUES (%s, %s, %s, %s, %s, 'pending');
        """,
        (sender_id, receiver_id, skill_offered, skill_requested, default_msg),
        commit=True
    )

    # Send Notification to Receiver
    execute_query(
        """
        INSERT INTO notifications (user_id, title, message, type, link)
        VALUES (%s, 'New Skill Exchange Request', %s, 'request', 'requests.html');
        """,
        (receiver_id, f"{sender_name} offered to teach you '{skill_offered}' in exchange for '{skill_requested}'."),
        commit=True
    )

    return jsonify({
        "success": True,
        "message": f"Skill exchange request sent to {receiver['full_name']}!",
        "request_id": request_id
    }), 201


@requests_bp.route("/received", methods=["GET"])
@login_required
def get_received_requests():
    user_id = session.get("user_id")

    requests_list = execute_query(
        """
        SELECT r.request_id, r.sender_id, r.receiver_id, r.skill_offered, 
               r.skill_requested, r.message, r.status, r.created_at,
               u.full_name AS sender_name, u.email AS sender_email,
               u.college_name AS sender_college, u.department AS sender_department,
               u.year_of_study AS sender_year, u.profile_image AS sender_avatar
        FROM skill_exchange_requests r
        JOIN users u ON r.sender_id = u.user_id
        WHERE r.receiver_id = %s
        ORDER BY 
            CASE r.status 
                WHEN 'pending' THEN 1 
                WHEN 'accepted' THEN 2 
                ELSE 3 
            END,
            r.created_at DESC;
        """,
        (user_id,),
        fetchall=True
    ) or []

    return jsonify({"success": True, "requests": requests_list}), 200


@requests_bp.route("/sent", methods=["GET"])
@login_required
def get_sent_requests():
    user_id = session.get("user_id")

    requests_list = execute_query(
        """
        SELECT r.request_id, r.sender_id, r.receiver_id, r.skill_offered, 
               r.skill_requested, r.message, r.status, r.created_at,
               u.full_name AS receiver_name, u.email AS receiver_email,
               u.college_name AS receiver_college, u.department AS receiver_department,
               u.year_of_study AS receiver_year, u.profile_image AS receiver_avatar
        FROM skill_exchange_requests r
        JOIN users u ON r.receiver_id = u.user_id
        WHERE r.sender_id = %s
        ORDER BY r.created_at DESC;
        """,
        (user_id,),
        fetchall=True
    ) or []

    return jsonify({"success": True, "requests": requests_list}), 200


@requests_bp.route("/connections", methods=["GET"])
@login_required
def get_connections():
    """List all accepted student connections for chat, sessions, and directory."""
    user_id = session.get("user_id")

    connections = execute_query(
        """
        SELECT c.connection_id, c.created_at AS connected_since,
               u.user_id, u.full_name, u.email, u.college_name, u.department, 
               u.year_of_study, u.bio, u.profile_image
        FROM connections c
        JOIN users u ON (CASE WHEN c.user1_id = %s THEN c.user2_id ELSE c.user1_id END) = u.user_id
        WHERE c.user1_id = %s OR c.user2_id = %s
        ORDER BY u.full_name ASC;
        """,
        (user_id, user_id, user_id),
        fetchall=True
    ) or []

    return jsonify({"success": True, "connections": connections, "total": len(connections)}), 200


@requests_bp.route("/<int:request_id>/status", methods=["PUT"])
@login_required
def update_request_status(request_id):
    user_id = session.get("user_id")
    user_name = session.get("full_name", "Student")
    data = request.get_json() or {}
    new_status = data.get("status", "").strip().lower()

    if new_status not in ["accepted", "rejected", "cancelled"]:
        return jsonify({"success": False, "message": "Invalid status value."}), 400

    req_record = execute_query(
        """
        SELECT r.*, u1.full_name AS sender_name, u2.full_name AS receiver_name
        FROM skill_exchange_requests r
        JOIN users u1 ON r.sender_id = u1.user_id
        JOIN users u2 ON r.receiver_id = u2.user_id
        WHERE r.request_id = %s;
        """,
        (request_id,),
        fetchone=True
    )

    if not req_record:
        return jsonify({"success": False, "message": "Request not found."}), 404

    sender_id = req_record["sender_id"]
    receiver_id = req_record["receiver_id"]

    if new_status in ["accepted", "rejected"]:
        if receiver_id != user_id:
            return jsonify({"success": False, "message": "Only the recipient can accept or reject this request."}), 403

        execute_query(
            "UPDATE skill_exchange_requests SET status = %s WHERE request_id = %s;",
            (new_status, request_id),
            commit=True
        )

        if new_status == "accepted":
            # Establish connection in `connections` table
            u1, u2 = min(sender_id, receiver_id), max(sender_id, receiver_id)
            execute_query(
                "INSERT IGNORE INTO connections (user1_id, user2_id) VALUES (%s, %s);",
                (u1, u2),
                commit=True
            )

            # Notify sender
            execute_query(
                """
                INSERT INTO notifications (user_id, title, message, type, link)
                VALUES (%s, 'Request Accepted! 🤝', %s, 'request', 'chat.html');
                """,
                (sender_id, f"{req_record['receiver_name']} accepted your request for {req_record['skill_offered']} ⇄ {req_record['skill_requested']}. You can now chat!"),
                commit=True
            )

            # Welcome message in chat
            execute_query(
                """
                INSERT INTO messages (sender_id, receiver_id, message_text)
                VALUES (%s, %s, %s);
                """,
                (receiver_id, sender_id, f"Hi {req_record['sender_name']}! I accepted your skill exchange for {req_record['skill_offered']} ⇄ {req_record['skill_requested']}. Let's coordinate our first session!"),
                commit=True
            )

        elif new_status == "rejected":
            execute_query(
                """
                INSERT INTO notifications (user_id, title, message, type, link)
                VALUES (%s, 'Request Declined', %s, 'request', 'requests.html');
                """,
                (sender_id, f"{req_record['receiver_name']} was unable to accept your exchange proposal."),
                commit=True
            )

        return jsonify({"success": True, "message": f"Request {new_status} successfully!", "status": new_status}), 200

    elif new_status == "cancelled":
        if sender_id != user_id:
            return jsonify({"success": False, "message": "Only the sender can cancel their pending request."}), 403

        execute_query(
            "UPDATE skill_exchange_requests SET status = 'cancelled' WHERE request_id = %s;",
            (request_id,),
            commit=True
        )
        return jsonify({"success": True, "message": "Request cancelled successfully.", "status": "cancelled"}), 200

