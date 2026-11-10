"""
End-to-End Automated Test Verification Suite for SkillSwap
Validates all backend APIs, database models, session security,
skill matching algorithm, chat messaging, and admin operations.
"""

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app import app
from database import init_db


def run_all_tests():
    print("=======================================================")
    print(" 🧪 Starting SkillSwap Verification Test Suite")
    print("=======================================================\n")

    # 1. Initialize Database
    init_db()
    client = app.test_client()

    # Test 1: Unauthenticated Guard
    print("1. Testing Authentication Guard...")
    res = client.get("/api/auth/me")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    print("✓ Passed 401 unauthenticated check.")

    # Test 2: Student Login as Rahul Sharma
    print("\n2. Testing Student Authentication (Rahul Sharma)...")
    res = client.post("/api/auth/login", json={"email": "rahul@college.edu", "password": "password123"})
    data = res.get_json()
    assert res.status_code == 200 and data["success"], f"Login failed: {data}"
    assert data["user"]["full_name"] == "Rahul Sharma"
    print(f"✓ Student authenticated: {data['user']['full_name']} (Role: {data['user']['role']})")

    # Test 3: Session Verification
    print("\n3. Testing Session Persistence...")
    res = client.get("/api/auth/me")
    data = res.get_json()
    assert res.status_code == 200 and data["authenticated"]
    print(f"✓ Active session confirmed for: {data['user']['full_name']}")

    # Test 4: Dashboard Aggregate API
    print("\n4. Testing Dashboard Aggregate Endpoint...")
    res = client.get("/api/dashboard")
    data = res.get_json()
    assert res.status_code == 200 and data["success"]
    stats = data["stats"]
    print(f"✓ Dashboard stats: Teaching={stats['teaching_count']}, Learning={stats['learning_count']}, Connections={stats['total_connections']}, Pending={stats['pending_requests']}")

    # Test 5: Intelligent Two-Way Skill Matching Algorithm
    print("\n5. Testing Skill Matching System (Reciprocal Pairing)...")
    res = client.get("/api/matching/recommendations")
    data = res.get_json()
    assert res.status_code == 200 and data["success"]
    top_match = data["recommendations"][0]
    print(f"✓ Top match for Rahul: {top_match['full_name']} ({top_match['match_badge']})")
    print(f"  Reason: {top_match['match_reason']}")
    assert top_match["match_score"] == 100, f"Expected 100% match score, got {top_match['match_score']}"
    assert top_match["user_id"] == 3, f"Expected Priya Patel (ID 3), got {top_match['user_id']}"
    print("✓ Reciprocal matching algorithm verified (Java ⇄ Python = 100% Mutual Match).")

    # Test 6: Skills Management API
    print("\n6. Testing Skills Management...")
    res = client.get("/api/skills")
    data = res.get_json()
    assert res.status_code == 200 and len(data["skills"]) >= 10
    print(f"✓ Retrieved {len(data['skills'])} master catalog skills.")

    # Test 7: Chat Messaging (Between Connected Peers)
    print("\n7. Testing Chat Module (Rahul & Connected Peer Priya)...")
    res = client.get("/api/chat/messages/3")
    data = res.get_json()
    assert res.status_code == 200 and data["success"]
    print(f"✓ Retrieved {len(data['messages'])} chat messages between Rahul & Priya.")

    res = client.post("/api/chat/messages", json={
        "receiver_id": 3,
        "message_text": "Automated test message: Are you ready for our peer session?"
    })
    data = res.get_json()
    assert res.status_code == 201 and data["success"]
    print("✓ Real-time message successfully posted.")

    # Test 8: Learning Sessions Scheduling
    print("\n8. Testing Learning Sessions Management...")
    res = client.get("/api/sessions")
    data = res.get_json()
    assert res.status_code == 200 and data["success"]
    print(f"✓ Found {len(data['upcoming'])} upcoming sessions and {len(data['past'])} past sessions.")

    # Test 9: Notifications API
    print("\n9. Testing Notifications Feed...")
    res = client.get("/api/notifications")
    data = res.get_json()
    assert res.status_code == 200 and data["success"]
    print(f"✓ Student has {len(data['notifications'])} notifications.")

    # Test 10: Admin Role-Based Access Control
    print("\n10. Testing Admin Authorization & System Metrics...")
    # Student accessing admin route -> must be 403 Forbidden
    res = client.get("/api/admin/stats")
    assert res.status_code == 403, "Student should NOT be able to access admin endpoints"
    print("✓ Student correctly forbidden from accessing admin endpoints (403 Forbidden).")

    # Log in as Administrator
    client.post("/api/auth/logout")
    res = client.post("/api/auth/login", json={"email": "admin@skillswap.edu", "password": "admin123"})
    data = res.get_json()
    assert res.status_code == 200 and data["user"]["role"] == "admin"
    print("✓ Administrator successfully authenticated.")

    res = client.get("/api/admin/stats")
    data = res.get_json()
    assert res.status_code == 200 and data["success"]
    astats = data["stats"]
    print(f"✓ Admin metrics: {astats['total_students']} Students, {astats['total_skills']} Skills, {astats['active_sessions']} Sessions.")

    print("\n=======================================================")
    print("🎉 ALL 10 COMPREHENSIVE TEST SUITES PASSED WITH 100% SUCCESS!")
    print("=======================================================\n")


if __name__ == "__main__":
    run_all_tests()

