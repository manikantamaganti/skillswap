"""
Skill Management Routes for SkillSwap
Handles master skill catalog, student teaching skills, and learning interests.
"""

from flask import Blueprint, request, jsonify, session
from database import execute_query
from auth import login_required

skills_bp = Blueprint("skills", __name__, url_prefix="/api/skills")


@skills_bp.route("", methods=["GET"])
def get_all_skills():
    """Return all skills categorized, with learner/teacher stats."""
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()

    query = """
        SELECT s.skill_id, s.skill_name, s.category,
               SUM(CASE WHEN ss.skill_type = 'teach' THEN 1 ELSE 0 END) AS teachers_count,
               SUM(CASE WHEN ss.skill_type = 'learn' THEN 1 ELSE 0 END) AS learners_count
        FROM skills s
        LEFT JOIN student_skills ss ON s.skill_id = ss.skill_id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND s.skill_name LIKE %s"
        params.append(f"%{search}%")

    if category and category.lower() != "all":
        query += " AND s.category = %s"
        params.append(category)

    query += " GROUP BY s.skill_id, s.skill_name, s.category ORDER BY s.category ASC, s.skill_name ASC;"

    skills = execute_query(query, params, fetchall=True) or []
    return jsonify({"success": True, "skills": skills}), 200


@skills_bp.route("/categories", methods=["GET"])
def get_categories():
    categories = execute_query(
        "SELECT DISTINCT category FROM skills ORDER BY category ASC;",
        fetchall=True
    ) or []
    return jsonify({
        "success": True,
        "categories": [c["category"] for c in categories]
    }), 200


@skills_bp.route("/my-skills", methods=["GET"])
@login_required
def get_my_skills():
    user_id = session.get("user_id")

    teaching = execute_query(
        """
        SELECT s.skill_id, s.skill_name, s.category, ss.created_at
        FROM student_skills ss
        JOIN skills s ON ss.skill_id = s.skill_id
        WHERE ss.user_id = %s AND ss.skill_type = 'teach'
        ORDER BY s.skill_name;
        """,
        (user_id,),
        fetchall=True
    ) or []

    learning = execute_query(
        """
        SELECT s.skill_id, s.skill_name, s.category, ss.created_at
        FROM student_skills ss
        JOIN skills s ON ss.skill_id = s.skill_id
        WHERE ss.user_id = %s AND ss.skill_type = 'learn'
        ORDER BY s.skill_name;
        """,
        (user_id,),
        fetchall=True
    ) or []

    return jsonify({
        "success": True,
        "teaching": teaching,
        "learning": learning
    }), 200


@skills_bp.route("/my-skills", methods=["POST"])
@login_required
def add_my_skill():
    user_id = session.get("user_id")
    data = request.get_json() or {}

    skill_id = data.get("skill_id")
    skill_name = data.get("skill_name", "").strip()
    category = data.get("category", "General").strip() or "General"
    skill_type = data.get("skill_type", "teach").strip().lower()

    if skill_type not in ["teach", "learn"]:
        return jsonify({"success": False, "message": "skill_type must be 'teach' or 'learn'."}), 400

    # Resolve or create skill
    if not skill_id and skill_name:
        existing = execute_query(
            "SELECT skill_id, skill_name, category FROM skills WHERE LOWER(skill_name) = LOWER(%s);",
            (skill_name,),
            fetchone=True
        )
        if existing:
            skill_id = existing["skill_id"]
        else:
            skill_id = execute_query(
                "INSERT INTO skills (skill_name, category) VALUES (%s, %s);",
                (skill_name, category),
                commit=True
            )

    if not skill_id:
        return jsonify({"success": False, "message": "Please specify a valid skill."}), 400

    # Check if already added
    exists = execute_query(
        "SELECT id FROM student_skills WHERE user_id = %s AND skill_id = %s AND skill_type = %s;",
        (user_id, skill_id, skill_type),
        fetchone=True
    )
    if exists:
        return jsonify({"success": False, "message": f"You have already added this skill to your '{skill_type}' list."}), 409

    execute_query(
        "INSERT INTO student_skills (user_id, skill_id, skill_type) VALUES (%s, %s, %s);",
        (user_id, skill_id, skill_type),
        commit=True
    )

    skill_info = execute_query("SELECT skill_id, skill_name, category FROM skills WHERE skill_id = %s;", (skill_id,), fetchone=True)

    return jsonify({
        "success": True,
        "message": f"Added '{skill_info['skill_name']}' to your {skill_type} skills!",
        "skill": skill_info,
        "skill_type": skill_type
    }), 201


@skills_bp.route("/my-skills/<int:skill_id>", methods=["DELETE"])
@login_required
def remove_my_skill(skill_id):
    user_id = session.get("user_id")
    skill_type = request.args.get("type", "teach").strip().lower()

    if skill_type not in ["teach", "learn"]:
        return jsonify({"success": False, "message": "type parameter must be 'teach' or 'learn'."}), 400

    deleted = execute_query(
        "DELETE FROM student_skills WHERE user_id = %s AND skill_id = %s AND skill_type = %s;",
        (user_id, skill_id, skill_type),
        commit=True
    )

    if deleted:
        return jsonify({"success": True, "message": f"Skill removed from your {skill_type} list."}), 200
    return jsonify({"success": False, "message": "Skill not found in your list."}), 404

