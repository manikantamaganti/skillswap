"""
Database Connection & Execution Helper for SkillSwap Platform
Supports MySQL via mysql-connector-python with automatic schema initialization
and resilient fallback for offline/local evaluation environments.
"""

import os
import re
import sqlite3
from pathlib import Path

# Database Configuration (Environment variables with sensible local defaults)
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "skillswap_db")
DB_PORT = int(os.environ.get("DB_PORT", 3306))

# Cloud Database URL support (e.g. Render / Railway / Aiven / TiDB)
_raw_db_url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL")
if _raw_db_url and ("mysql" in _raw_db_url):
    try:
        from urllib.parse import urlparse
        _parsed = urlparse(_raw_db_url)
        DB_HOST = _parsed.hostname or DB_HOST
        DB_USER = _parsed.username or DB_USER
        DB_PASSWORD = _parsed.password or DB_PASSWORD
        DB_NAME = _parsed.path.lstrip('/') or DB_NAME
        if _parsed.port:
            DB_PORT = int(_parsed.port)
    except Exception as _e:
        print(f"[SkillSwap Database] Error parsing DATABASE_URL: {_e}")

BASE_DIR = Path(__file__).resolve().parent.parent
SQL_SCHEMA_FILE = BASE_DIR / "database" / "skillswap_db.sql"
SQLITE_DB_FILE = BASE_DIR / "database" / "skillswap_local.db"

DB_ENGINE = "mysql"
_mysql_available = False

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    _mysql_module_loaded = True
except ImportError:
    _mysql_module_loaded = False
    MySQLError = Exception


def test_mysql_connection():
    """Test if MySQL server is reachable with the current configuration."""
    global DB_ENGINE, _mysql_available
    if not _mysql_module_loaded:
        DB_ENGINE = "sqlite"
        return False

    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            connection_timeout=2
        )
        if conn.is_connected():
            conn.close()
            DB_ENGINE = "mysql"
            _mysql_available = True
            return True
    except Exception:
        DB_ENGINE = "sqlite"
        _mysql_available = False
        return False
    return False


def get_db_connection():
    """Returns an active database connection."""
    global DB_ENGINE
    if DB_ENGINE == "mysql":
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT,
                autocommit=True
            )
            return conn
        except Exception:
            pass

    # SQLite fallback connection
    conn = sqlite3.connect(str(SQLITE_DB_FILE))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def execute_query(query, params=None, fetchone=False, fetchall=False, commit=False):
    """
    Execute a parameterized SQL query safely.
    Handles differences between MySQL (%s) and SQLite (?) automatically.
    """
    global DB_ENGINE
    if params is None:
        params = ()
    elif isinstance(params, list):
        params = tuple(params)

    conn = get_db_connection()

    if DB_ENGINE == "mysql":
        cursor = conn.cursor(dictionary=True, buffered=True)
        try:
            cursor.execute(query, params)
            if commit:
                conn.commit()
                last_id = cursor.lastrowid
                row_count = cursor.rowcount
                cursor.close()
                conn.close()
                return last_id if last_id else row_count

            if fetchone:
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                return result

            if fetchall:
                result = cursor.fetchall()
                cursor.close()
                conn.close()
                return result

            cursor.close()
            conn.close()
            return None
        except Exception as err:
            cursor.close()
            conn.close()
            raise err

    else:
        # SQLite mode: convert MySQL %s placeholders to SQLite ?
        sqlite_query = query.replace("%s", "?")
        sqlite_query = re.sub(r'DATE_SUB\(NOW\(\),\s*INTERVAL\s*(\d+)\s*DAY\)', r"datetime('now', '-\1 days')", sqlite_query, flags=re.IGNORECASE)
        sqlite_query = re.sub(r'DATE_ADD\(CURRENT_DATE,\s*INTERVAL\s*(\d+)\s*DAY\)', r"date('now', '+\1 days')", sqlite_query, flags=re.IGNORECASE)
        sqlite_query = re.sub(r'DATE_SUB\(CURRENT_DATE,\s*INTERVAL\s*(\d+)\s*DAY\)', r"date('now', '-\1 days')", sqlite_query, flags=re.IGNORECASE)
        sqlite_query = re.sub(r'NOW\(\)', r"datetime('now')", sqlite_query, flags=re.IGNORECASE)
        sqlite_query = re.sub(r'CURRENT_DATE', r"date('now')", sqlite_query, flags=re.IGNORECASE)

        cursor = conn.cursor()
        try:
            cursor.execute(sqlite_query, params)
            if commit:
                conn.commit()
                last_id = cursor.lastrowid
                row_count = cursor.rowcount
                cursor.close()
                conn.close()
                return last_id if last_id else row_count

            if fetchone:
                row = cursor.fetchone()
                result = dict(row) if row else None
                cursor.close()
                conn.close()
                return result

            if fetchall:
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
                cursor.close()
                conn.close()
                return result

            cursor.close()
            conn.close()
            return None
        except Exception as err:
            cursor.close()
            conn.close()
            raise err


def init_db():
    """Initializes the database schema and sample data."""
    global DB_ENGINE
    mysql_live = test_mysql_connection()

    if mysql_live:
        print(f"[SkillSwap Database] Connected to MySQL Server at {DB_HOST}:{DB_PORT}.")
        try:
            root_conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT
            )
            root_cursor = root_conn.cursor()
            root_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            root_cursor.close()
            root_conn.close()

            db_conn = get_db_connection()
            check_cursor = db_conn.cursor()
            check_cursor.execute("SHOW TABLES LIKE 'users';")
            exists = check_cursor.fetchone()
            check_cursor.close()

            if not exists:
                print(f"[SkillSwap Database] Initializing MySQL tables & sample data from {SQL_SCHEMA_FILE.name}...")
                _execute_sql_file_mysql(db_conn, SQL_SCHEMA_FILE)
                print("[SkillSwap Database] MySQL database initialized successfully.")
            else:
                print("[SkillSwap Database] MySQL tables verified.")
            db_conn.close()
            return
        except Exception as e:
            print(f"[SkillSwap Database] MySQL setup encountered error: {e}. Switching to resilient local engine.")
            DB_ENGINE = "sqlite"

    print(f"[SkillSwap Database] Operating in resilient local database mode ({SQLITE_DB_FILE.name}).")
    _init_sqlite()


def _execute_sql_file_mysql(conn, filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        sql_content = f.read()

    statements = sql_content.split(";")
    cursor = conn.cursor()
    for stmt in statements:
        stmt = stmt.strip()
        if stmt and not stmt.lower().startswith("create database") and not stmt.lower().startswith("use "):
            try:
                cursor.execute(stmt)
            except Exception:
                pass
    conn.commit()
    cursor.close()


def _init_sqlite():
    SQLITE_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_DB_FILE))
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        college_name TEXT NOT NULL,
        department TEXT NOT NULL,
        year_of_study TEXT NOT NULL,
        bio TEXT,
        profile_image TEXT DEFAULT 'default_avatar.png',
        role TEXT DEFAULT 'student',
        status TEXT DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS skills (
        skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill_name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS student_skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        skill_id INTEGER NOT NULL,
        skill_type TEXT NOT NULL CHECK(skill_type IN ('teach', 'learn')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE,
        UNIQUE(user_id, skill_id, skill_type)
    );

    CREATE TABLE IF NOT EXISTS skill_exchange_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        skill_offered TEXT NOT NULL,
        skill_requested TEXT NOT NULL,
        message TEXT,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected', 'cancelled')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (receiver_id) REFERENCES users(user_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS connections (
        connection_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1_id INTEGER NOT NULL,
        user2_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user1_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (user2_id) REFERENCES users(user_id) ON DELETE CASCADE,
        UNIQUE(user1_id, user2_id)
    );

    CREATE TABLE IF NOT EXISTS messages (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        message_text TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (receiver_id) REFERENCES users(user_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS learning_sessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        host_id INTEGER NOT NULL,
        partner_id INTEGER NOT NULL,
        session_title TEXT NOT NULL,
        skill_name TEXT NOT NULL,
        session_date TEXT NOT NULL,
        session_time TEXT NOT NULL,
        description TEXT,
        meeting_link TEXT,
        status TEXT DEFAULT 'upcoming' CHECK(status IN ('upcoming', 'completed', 'cancelled')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (host_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (partner_id) REFERENCES users(user_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        type TEXT DEFAULT 'info',
        link TEXT,
        is_read INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM users;")
    count = cursor.fetchone()[0]
    if count == 0:
        _seed_sqlite(cursor)
        conn.commit()
        print("[SkillSwap Database] Local database initialized with 11 sample users, skills, sessions & chats.")
    cursor.close()
    conn.close()


def _seed_sqlite(cursor):
    # 1. Skills
    skills_data = [
        (1, 'Java', 'Programming'),
        (2, 'Python', 'Programming'),
        (3, 'C Programming', 'Programming'),
        (4, 'Data Structures', 'Programming'),
        (5, 'HTML & CSS', 'Web Development'),
        (6, 'JavaScript', 'Web Development'),
        (7, 'React JS', 'Web Development'),
        (8, 'Node JS', 'Web Development'),
        (9, 'SQL', 'Databases'),
        (10, 'MongoDB', 'Databases'),
        (11, 'Machine Learning', 'Data Science & AI'),
        (12, 'Data Analytics', 'Data Science & AI'),
        (13, 'Graphic Design', 'Design & UI/UX'),
        (14, 'UI/UX Design', 'Design & UI/UX'),
        (15, 'Communication Skills', 'Soft Skills'),
        (16, 'Public Speaking', 'Soft Skills')
    ]
    cursor.executemany("INSERT OR IGNORE INTO skills (skill_id, skill_name, category) VALUES (?, ?, ?);", skills_data)

    # 2. Users
    admin_hash = 'scrypt:32768:8:1$luuNaI6RHI9EH0i3$7ea7d8494fec71116d0a6839c30804612e804cdb64b879fa362fd49e79747353ab909fa46e6a4c5dd92b73a69c5343be102057387ef2dca7c366128ba942cd50'
    student_hash = 'scrypt:32768:8:1$X6EIwKzlz0j82Lmb$ced50e9c8e5ed140e8f2f11f1d1a5c024c0e8af5236c0f275f71fe5564fba2ead515802e1e90bcadd982c25b1030e373bcca2bc18370664e59cfd4a6e87af146'

    users_data = [
        (1, 'System Administrator', 'admin@skillswap.edu', admin_hash, 'SkillSwap University', 'Administration', 'Staff', 'Platform manager maintaining community guidelines and technical stability.', 'default_avatar.png', 'admin', 'active'),
        (2, 'Rahul Sharma', 'rahul@college.edu', student_hash, 'National Institute of Technology', 'Computer Science', '3rd Year', 'Experienced Java coder and DSA problem solver. Looking forward to learning Python for ML and scripting.', 'avatar1.png', 'student', 'active'),
        (3, 'Priya Patel', 'priya@college.edu', student_hash, 'National Institute of Technology', 'Information Technology', '3rd Year', 'Passionate Python developer building data scripts. Eager to master Java and object-oriented backend patterns.', 'avatar2.png', 'student', 'active'),
        (4, 'Kiran Rao', 'kiran@college.edu', student_hash, 'City Engineering College', 'Computer Science', '2nd Year', 'Frontend enthusiast skilled in HTML & CSS responsive layouts. Looking to master modern JavaScript and DOM.', 'avatar3.png', 'student', 'active'),
        (5, 'Sita Kumari', 'sita@college.edu', student_hash, 'City Engineering College', 'Computer Science', '2nd Year', 'JavaScript and web logic builder. Want to polish advanced CSS animations and modern layout systems.', 'avatar4.png', 'student', 'active'),
        (6, 'Arun Kumar', 'arun@college.edu', student_hash, 'State Technical University', 'Information Science', '4th Year', 'Database administrator skilled in SQL queries, indexing, and joins. Eager to pick up Python fundamentals.', 'avatar5.png', 'student', 'active'),
        (7, 'Ananya Iyer', 'ananya@college.edu', student_hash, 'State Technical University', 'Data Science & AI', '3rd Year', 'Python programmer focused on statistical modeling. Seeking deep relational SQL and database optimization skills.', 'avatar6.png', 'student', 'active'),
        (8, 'Vikram Singh', 'vikram@college.edu', student_hash, 'Apex School of Technology', 'Digital Media', '3rd Year', 'UI/UX and Graphic Designer proficient in Figma and Canva. Looking to learn HTML & CSS frontend coding.', 'avatar7.png', 'student', 'active'),
        (9, 'Neha Gupta', 'neha@college.edu', student_hash, 'Apex School of Technology', 'Computer Science', '3rd Year', 'Frontend web developer creating web interfaces. Want to collaborate with a graphic/UI designer to learn design thinking.', 'avatar8.png', 'student', 'active'),
        (10, 'Rohan Verma', 'rohan@college.edu', student_hash, 'Metro Institute of Tech', 'Electronics', '2nd Year', 'C programming and embedded hardware explorer. Interested in learning Python for robotics scripts.', 'avatar9.png', 'student', 'active'),
        (11, 'Meera Nambiar', 'meera@college.edu', student_hash, 'Metro Institute of Tech', 'Business Administration', '4th Year', 'Public speaker and campus debate mentor. Wanting to learn Python for business analytics and automation.', 'avatar10.png', 'student', 'active')
    ]
    cursor.executemany("INSERT OR IGNORE INTO users (user_id, full_name, email, password_hash, college_name, department, year_of_study, bio, profile_image, role, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", users_data)

    # 3. Student Skills
    student_skills_data = [
        (2, 1, 'teach'), (2, 4, 'teach'), (2, 2, 'learn'), (2, 11, 'learn'),
        (3, 2, 'teach'), (3, 11, 'teach'), (3, 1, 'learn'), (3, 4, 'learn'),
        (4, 5, 'teach'), (4, 6, 'learn'), (4, 7, 'learn'),
        (5, 6, 'teach'), (5, 7, 'teach'), (5, 5, 'learn'), (5, 13, 'learn'),
        (6, 9, 'teach'), (6, 2, 'learn'), (6, 12, 'learn'),
        (7, 2, 'teach'), (7, 12, 'teach'), (7, 9, 'learn'), (7, 10, 'learn'),
        (8, 13, 'teach'), (8, 14, 'teach'), (8, 5, 'learn'), (8, 6, 'learn'),
        (9, 5, 'teach'), (9, 6, 'teach'), (9, 13, 'learn'), (9, 14, 'learn'),
        (10, 3, 'teach'), (10, 2, 'learn'),
        (11, 15, 'teach'), (11, 16, 'teach'), (11, 2, 'learn')
    ]
    cursor.executemany("INSERT OR IGNORE INTO student_skills (user_id, skill_id, skill_type) VALUES (?, ?, ?);", student_skills_data)

    # 4. Requests
    requests_data = [
        (1, 2, 3, 'Java', 'Python', 'Hey Priya, I noticed you are skilled in Python. Would love to teach you Java OOP in exchange for Python data scripting!', 'accepted', "datetime('now', '-5 days')"),
        (2, 4, 5, 'HTML & CSS', 'JavaScript', 'Hi Sita! I can help you with modern CSS flex/grid layout if you can mentor me in JavaScript async/await.', 'accepted', "datetime('now', '-4 days')"),
        (3, 6, 7, 'SQL', 'Python', 'Hello Ananya! Need assistance in relational query tuning? I want to learn Python pandas from you.', 'accepted', "datetime('now', '-3 days')"),
        (4, 8, 9, 'UI/UX Design', 'HTML & CSS', 'Hi Neha! Would love to exchange Figma wireframing for your HTML/CSS coding expertise.', 'pending', "datetime('now', '-2 days')"),
        (5, 10, 2, 'C Programming', 'Java', 'Hi Rahul, can we connect? I can teach C pointer fundamentals in exchange for Java help.', 'pending', "datetime('now', '-1 days')"),
        (6, 11, 3, 'Public Speaking', 'Python', 'Hello Priya, looking forward to trading interview speech techniques for Python basics.', 'pending', "datetime('now')")
    ]
    for r in requests_data:
        cursor.execute(f"INSERT OR IGNORE INTO skill_exchange_requests (request_id, sender_id, receiver_id, skill_offered, skill_requested, message, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, {r[7]});", r[:7])

    # 5. Connections
    connections_data = [
        (1, 2, 3, "datetime('now', '-5 days')"),
        (2, 4, 5, "datetime('now', '-4 days')"),
        (3, 6, 7, "datetime('now', '-3 days')")
    ]
    for c in connections_data:
        cursor.execute(f"INSERT OR IGNORE INTO connections (connection_id, user1_id, user2_id, created_at) VALUES (?, ?, ?, {c[3]});", c[:3])

    # 6. Messages
    messages_data = [
        (1, 2, 3, 'Hi Priya! Glad to connect on SkillSwap. When are you free for our first Java / Python exchange?', 1, "datetime('now', '-4 days')"),
        (2, 3, 2, 'Hey Rahul! Excited to learn Java. I am free this Saturday at 4 PM. We can start with Python basics first!', 1, "datetime('now', '-4 days')"),
        (3, 2, 3, 'Sounds great! I scheduled our first session on the Sessions page with a Google Meet link.', 1, "datetime('now', '-3 days')"),
        (4, 4, 5, 'Hi Sita, I reviewed your CSS question. Flexbox wrap with gap will solve your layout issue nicely.', 1, "datetime('now', '-2 days')"),
        (5, 5, 4, 'Thanks Kiran! That worked perfectly. Let me know when you want to dive into JavaScript DOM events.', 0, "datetime('now', '-1 days')")
    ]
    for m in messages_data:
        cursor.execute(f"INSERT OR IGNORE INTO messages (message_id, sender_id, receiver_id, message_text, is_read, timestamp) VALUES (?, ?, ?, ?, ?, {m[5]});", m[:5])

    # 7. Sessions
    sessions_data = [
        (1, 2, 3, 'Java OOP & Class Design Workshop', 'Java', "date('now', '+2 days')", '16:00:00', 'Introduction to Java classes, encapsulation, inheritance, and code examples.', 'https://meet.google.com/abc-defg-hij', 'upcoming', "datetime('now')"),
        (2, 3, 2, 'Python Data Scripting & Pandas Intro', 'Python', "date('now', '+4 days')", '17:30:00', 'Hands-on session covering Python dictionary comprehension, list slices, and functions.', 'https://meet.google.com/xyz-uvwx-rst', 'upcoming', "datetime('now')"),
        (3, 4, 5, 'Modern CSS Grid Deep Dive', 'HTML & CSS', "date('now', '-2 days')", '15:00:00', 'Two-dimensional grid layouts, template areas, and mobile responsiveness.', 'https://meet.google.com/qwe-rtyu-iop', 'completed', "datetime('now', '-3 days')")
    ]
    for s in sessions_data:
        cursor.execute(f"INSERT OR IGNORE INTO learning_sessions (session_id, host_id, partner_id, session_title, skill_name, session_date, session_time, description, meeting_link, status, created_at) VALUES (?, ?, ?, ?, ?, {s[5]}, ?, ?, ?, ?, {s[10]});", (s[0], s[1], s[2], s[3], s[4], s[6], s[7], s[8], s[9]))

    # 8. Notifications
    notifs_data = [
        (1, 2, 'Exchange Request Accepted', 'Priya Patel accepted your skill exchange proposal for Java ⇄ Python.', 'request', 'requests.html', 1, "datetime('now', '-5 days')"),
        (2, 2, 'New Learning Session Scheduled', 'Upcoming session: Java OOP & Class Design Workshop is set for this weekend.', 'session', 'sessions.html', 0, "datetime('now')"),
        (3, 2, 'New Connection', 'You and Priya Patel are now connected! You can now chat and organize learning sessions.', 'connection', 'chat.html', 1, "datetime('now', '-5 days')"),
        (4, 3, 'New Message', 'Rahul Sharma sent you a message: "Sounds great! I scheduled our first session..."', 'message', 'chat.html', 0, "datetime('now', '-3 days')"),
        (5, 9, 'New Exchange Request', 'Vikram Singh sent you an exchange request: UI/UX Design for HTML & CSS.', 'request', 'requests.html', 0, "datetime('now', '-2 days')")
    ]
    for n in notifs_data:
        cursor.execute(f"INSERT OR IGNORE INTO notifications (notification_id, user_id, title, message, type, link, is_read, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, {n[7]});", n[:7])


if __name__ == "__main__":
    init_db()

