"""
Chat & Direct Messaging Module for SkillSwap
Restricted strictly to connected students; persists conversation history in MySQL.
"""

from flask import Blueprint, request, jsonify, session
from database import execute_query
from auth import login_required

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


def are_students_connected(u1, u2):
    min_id, max_id = min(u1, u2), max(u1, u2)
    conn = execute_query(
        "SELECT connection_id FROM connections WHERE user1_id = %s AND user2_id = %s;",
        (min_id, max_id),
        fetchone=True
    )
    return conn is not None


@chat_bp.route("/contacts", methods=["GET"])
@login_required
def get_chat_contacts():
    user_id = session.get("user_id")

    # Get all connected peers
    contacts = execute_query(
        """
        SELECT u.user_id, u.full_name, u.email, u.college_name, u.department, 
               u.profile_image, c.created_at AS connected_since,
               (
                   SELECT m.message_text FROM messages m 
                   WHERE (m.sender_id = u.user_id AND m.receiver_id = %s)
                      OR (m.sender_id = %s AND m.receiver_id = u.user_id)
                   ORDER BY m.timestamp DESC LIMIT 1
               ) AS last_message,
               (
                   SELECT m.timestamp FROM messages m 
                   WHERE (m.sender_id = u.user_id AND m.receiver_id = %s)
                      OR (m.sender_id = %s AND m.receiver_id = u.user_id)
                   ORDER BY m.timestamp DESC LIMIT 1
               ) AS last_timestamp,
               (
                   SELECT COUNT(*) FROM messages m 
                   WHERE m.sender_id = u.user_id AND m.receiver_id = %s AND m.is_read = 0
               ) AS unread_count
        FROM connections c
        JOIN users u ON (CASE WHEN c.user1_id = %s THEN c.user2_id ELSE c.user1_id END) = u.user_id
        WHERE c.user1_id = %s OR c.user2_id = %s
        ORDER BY last_timestamp DESC, u.full_name ASC;
        """,
        (user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id),
        fetchall=True
    ) or []

    return jsonify({"success": True, "contacts": contacts}), 200


@chat_bp.route("/messages/<int:partner_id>", methods=["GET"])
@login_required
def get_conversation(partner_id):
    user_id = session.get("user_id")

    if not are_students_connected(user_id, partner_id):
        return jsonify({"success": False, "message": "You can only chat with students you are connected with."}), 403

    partner = execute_query(
        "SELECT user_id, full_name, college_name, department, profile_image FROM users WHERE user_id = %s;",
        (partner_id,),
        fetchone=True
    )
    if not partner:
        return jsonify({"success": False, "message": "Partner not found."}), 404

    # Fetch message history
    messages = execute_query(
        """
        SELECT message_id, sender_id, receiver_id, message_text, is_read, timestamp
        FROM messages
        WHERE (sender_id = %s AND receiver_id = %s)
           OR (sender_id = %s AND receiver_id = %s)
        ORDER BY timestamp ASC;
        """,
        (user_id, partner_id, partner_id, user_id),
        fetchall=True
    ) or []

    # Mark unread messages from partner as read
    execute_query(
        "UPDATE messages SET is_read = 1 WHERE sender_id = %s AND receiver_id = %s AND is_read = 0;",
        (partner_id, user_id),
        commit=True
    )

    return jsonify({
        "success": True,
        "partner": partner,
        "messages": messages
    }), 200


@chat_bp.route("/messages", methods=["POST"])
@login_required
def send_message():
    sender_id = session.get("user_id")
    sender_name = session.get("full_name", "Connected Student")
    data = request.get_json() or {}

    receiver_id = data.get("receiver_id")
    message_text = data.get("message_text", "").strip()

    if not receiver_id or not message_text:
        return jsonify({"success": False, "message": "Receiver ID and message text are required."}), 400

    try:
        receiver_id = int(receiver_id)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid receiver ID."}), 400

    if not are_students_connected(sender_id, receiver_id):
        return jsonify({"success": False, "message": "You must be connected with this student to exchange messages."}), 403

    msg_id = execute_query(
        """
        INSERT INTO messages (sender_id, receiver_id, message_text, is_read)
        VALUES (%s, %s, %s, 0);
        """,
        (sender_id, receiver_id, message_text),
        commit=True
    )

    # Optional Notification to recipient
    snippet = message_text[:60] + ("..." if len(message_text) > 60 else "")
    execute_query(
        """
        INSERT INTO notifications (user_id, title, message, type, link)
        VALUES (%s, 'New Message Received', %s, 'message', 'chat.html');
        """,
        (receiver_id, f"{sender_name}: {snippet}"),
        commit=True
    )

    return jsonify({
        "success": True,
        "message": "Message sent successfully!",
        "message_id": msg_id,
        "message_data": {
            "message_id": msg_id,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message_text": message_text,
            "is_read": 0
        }
    }), 201

