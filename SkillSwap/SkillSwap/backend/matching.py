"""
Intelligent Skill Matching Algorithm & Student Discovery Directory
Calculates reciprocal compatibility percentages and matching skill intersections.
"""

from flask import Blueprint, request, jsonify, session
from database import execute_query
from auth import login_required

matching_bp = Blueprint("matching", __name__, url_prefix="/api/matching")


def calculate_student_matches(current_user_id, student_records):
    """
    Computes intelligent skill matching scores and reciprocal metadata
    between the current student and a list of candidate peers.
    """
    # 1. Fetch current user's skills
    my_teaching = execute_query(
        """
        SELECT s.skill_id, s.skill_name, s.category
        FROM student_skills ss
        JOIN skills s ON ss.skill_id = s.skill_id
        WHERE ss.user_id = %s AND ss.skill_type = 'teach';
        """,
        (current_user_id,),
        fetchall=True
    ) or []

    my_learning = execute_query(
        """
        SELECT s.skill_id, s.skill_name, s.category
        FROM student_skills ss
        JOIN skills s ON ss.skill_id = s.skill_id
        WHERE ss.user_id = %s AND ss.skill_type = 'learn';
        """,
        (current_user_id,),
        fetchall=True
    ) or []

    my_teach_map = {s["skill_id"]: s["skill_name"] for s in my_teaching}
    my_learn_map = {s["skill_id"]: s["skill_name"] for s in my_learning}

    # Fetch existing connections and pending requests to show status
    connections_records = execute_query(
        "SELECT user1_id, user2_id FROM connections WHERE user1_id = %s OR user2_id = %s;",
        (current_user_id, current_user_id),
        fetchall=True
    ) or []
    connected_ids = set()
    for c in connections_records:
        connected_ids.add(c["user2_id"] if c["user1_id"] == current_user_id else c["user1_id"])

    pending_records = execute_query(
        "SELECT receiver_id FROM skill_exchange_requests WHERE sender_id = %s AND status = 'pending';",
        (current_user_id,),
        fetchall=True
    ) or []
    pending_ids = {p["receiver_id"] for p in pending_records}

    results = []

    for peer in student_records:
        peer_id = peer["user_id"]
        if peer_id == current_user_id:
            continue

        peer_teaching = execute_query(
            """
            SELECT s.skill_id, s.skill_name, s.category
            FROM student_skills ss
            JOIN skills s ON ss.skill_id = s.skill_id
            WHERE ss.user_id = %s AND ss.skill_type = 'teach';
            """,
            (peer_id,),
            fetchall=True
        ) or []

        peer_learning = execute_query(
            """
            SELECT s.skill_id, s.skill_name, s.category
            FROM student_skills ss
            JOIN skills s ON ss.skill_id = s.skill_id
            WHERE ss.user_id = %s AND ss.skill_type = 'learn';
            """,
            (peer_id,),
            fetchall=True
        ) or []

        peer_teach_map = {s["skill_id"]: s["skill_name"] for s in peer_teaching}
        peer_learn_map = {s["skill_id"]: s["skill_name"] for s in peer_learning}

        # Intersections
        # 1. They teach what you want to learn:
        they_teach_you_want_ids = set(peer_teach_map.keys()).intersection(set(my_learn_map.keys()))
        they_teach_you_want_names = [peer_teach_map[sid] for sid in they_teach_you_want_ids]

        # 2. You teach what they want to learn:
        you_teach_they_want_ids = set(my_teach_map.keys()).intersection(set(peer_learn_map.keys()))
        you_teach_they_want_names = [my_teach_map[sid] for sid in you_teach_they_want_ids]

        # Score & classification
        match_score = 0
        match_badge = ""
        match_type = "general"
        match_reason = ""

        if they_teach_you_want_ids and you_teach_they_want_ids:
            # High Priority Mutual Exchange!
            match_score = 100
            match_badge = "100% Mutual Match"
            match_type = "mutual"
            match_reason = f"Perfect Exchange! You can teach them {', '.join(you_teach_they_want_names)} and learn {', '.join(they_teach_you_want_names)}."
        elif they_teach_you_want_ids:
            match_score = 75
            match_badge = "75% Match (Offers Desired Skill)"
            match_type = "teaches_wanted"
            match_reason = f"Can teach you {', '.join(they_teach_you_want_names)}."
        elif you_teach_they_want_ids:
            match_score = 50
            match_badge = "50% Match (Seeks Your Skill)"
            match_type = "wants_taught"
            match_reason = f"Seeking to learn {', '.join(you_teach_they_want_names)} from you."
        else:
            match_score = 25
            match_badge = "25% General Peer"
            match_type = "general"
            match_reason = "Connect and discuss custom study collaboration."

        results.append({
            "user_id": peer["user_id"],
            "full_name": peer["full_name"],
            "email": peer["email"],
            "college_name": peer["college_name"],
            "department": peer["department"],
            "year_of_study": peer["year_of_study"],
            "bio": peer["bio"],
            "profile_image": peer["profile_image"],
            "teaching_skills": peer_teaching,
            "learning_skills": peer_learning,
            "matching_teaches": they_teach_you_want_names,
            "matching_learns": you_teach_they_want_names,
            "match_score": match_score,
            "match_badge": match_badge,
            "match_type": match_type,
            "match_reason": match_reason,
            "is_connected": (peer_id in connected_ids),
            "has_pending_request": (peer_id in pending_ids)
        })

    # Sort by match score descending, then by name
    results.sort(key=lambda x: (x["match_score"], x["full_name"]), reverse=True)
    return results


@matching_bp.route("/recommendations", methods=["GET"])
@login_required
def get_recommendations():
    """Returns top smart matching peers for the dashboard."""
    current_user_id = session.get("user_id")

    candidates = execute_query(
        "SELECT * FROM users WHERE user_id != %s AND role = 'student' AND status = 'active';",
        (current_user_id,),
        fetchall=True
    ) or []

    matches = calculate_student_matches(current_user_id, candidates)
    return jsonify({"success": True, "recommendations": matches[:4]}), 200


@matching_bp.route("/partners", methods=["GET"])
def find_partners():
    """Directory search with filters: department, category, skill name, search query."""
    current_user_id = session.get("user_id")

    search = request.args.get("search", "").strip()
    department = request.args.get("department", "").strip()
    category = request.args.get("category", "").strip()
    skill_filter = request.args.get("skill", "").strip()

    query = "SELECT * FROM users WHERE role = 'student' AND status = 'active'"
    params = []

    if search:
        query += """ AND (
            full_name LIKE %s OR 
            department LIKE %s OR 
            college_name LIKE %s OR
            user_id IN (
                SELECT ss.user_id FROM student_skills ss
                JOIN skills sk ON ss.skill_id = sk.skill_id
                WHERE sk.skill_name LIKE %s
            )
        )"""
        sw = f"%{search}%"
        params.extend([sw, sw, sw, sw])

    if department and department.lower() != "all":
        query += " AND department = %s"
        params.append(department)

    if category and category.lower() != "all":
        query += """ AND user_id IN (
            SELECT ss.user_id FROM student_skills ss
            JOIN skills sk ON ss.skill_id = sk.skill_id
            WHERE sk.category = %s
        )"""
        params.append(category)

    if skill_filter and skill_filter.lower() != "all":
        query += """ AND user_id IN (
            SELECT ss.user_id FROM student_skills ss
            JOIN skills sk ON ss.skill_id = sk.skill_id
            WHERE LOWER(sk.skill_name) = LOWER(%s)
        )"""
        params.append(skill_filter)

    query += " ORDER BY full_name ASC;"

    candidates = execute_query(query, params, fetchall=True) or []

    if current_user_id:
        partners = calculate_student_matches(current_user_id, candidates)
    else:
        # Public mode without login: compute basic skill attachments
        partners = []
        for p in candidates:
            p_teach = execute_query(
                "SELECT s.skill_id, s.skill_name, s.category FROM student_skills ss JOIN skills s ON ss.skill_id = s.skill_id WHERE ss.user_id = %s AND ss.skill_type = 'teach';",
                (p["user_id"],), fetchall=True) or []
            p_learn = execute_query(
                "SELECT s.skill_id, s.skill_name, s.category FROM student_skills ss JOIN skills s ON ss.skill_id = s.skill_id WHERE ss.user_id = %s AND ss.skill_type = 'learn';",
                (p["user_id"],), fetchall=True) or []
            partners.append({
                "user_id": p["user_id"],
                "full_name": p["full_name"],
                "college_name": p["college_name"],
                "department": p["department"],
                "year_of_study": p["year_of_study"],
                "bio": p["bio"],
                "profile_image": p["profile_image"],
                "teaching_skills": p_teach,
                "learning_skills": p_learn,
                "match_score": 0,
                "match_badge": "Available Peer",
                "match_reason": "Log in to see your personalized skill compatibility score.",
                "is_connected": False,
                "has_pending_request": False
            })

    # Available department filters
    departments = execute_query(
        "SELECT DISTINCT department FROM users WHERE role = 'student' ORDER BY department ASC;",
        fetchall=True
    ) or []

    return jsonify({
        "success": True,
        "partners": partners,
        "departments": [d["department"] for d in departments],
        "total": len(partners)
    }), 200

