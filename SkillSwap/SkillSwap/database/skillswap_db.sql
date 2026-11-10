-- ===================================================================
-- SkillSwap Database Schema & Seed Data
-- Database Name: skillswap_db
-- Technology: MySQL (Compatible with MySQL 5.7, 8.0, and MariaDB)
-- ===================================================================

CREATE DATABASE IF NOT EXISTS `skillswap_db`
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE `skillswap_db`;

-- Drop existing tables in reverse dependency order
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `notifications`;
DROP TABLE IF EXISTS `learning_sessions`;
DROP TABLE IF EXISTS `messages`;
DROP TABLE IF EXISTS `connections`;
DROP TABLE IF EXISTS `skill_exchange_requests`;
DROP TABLE IF EXISTS `student_skills`;
DROP TABLE IF EXISTS `skills`;
DROP TABLE IF EXISTS `users`;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. Users Table (Students & Admins)
CREATE TABLE `users` (
    `user_id` INT AUTO_INCREMENT PRIMARY KEY,
    `full_name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `college_name` VARCHAR(150) NOT NULL,
    `department` VARCHAR(100) NOT NULL,
    `year_of_study` VARCHAR(20) NOT NULL,
    `bio` TEXT,
    `profile_image` VARCHAR(255) DEFAULT 'default_avatar.png',
    `role` ENUM('student', 'admin') DEFAULT 'student',
    `status` ENUM('active', 'suspended') DEFAULT 'active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Master Skills Table
CREATE TABLE `skills` (
    `skill_id` INT AUTO_INCREMENT PRIMARY KEY,
    `skill_name` VARCHAR(100) NOT NULL UNIQUE,
    `category` VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Student Skills Table (Teaching & Learning Associations)
CREATE TABLE `student_skills` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `skill_id` INT NOT NULL,
    `skill_type` ENUM('teach', 'learn') NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_student_skills_user` FOREIGN KEY (`user_id`)
        REFERENCES `users`(`user_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_student_skills_skill` FOREIGN KEY (`skill_id`)
        REFERENCES `skills`(`skill_id`) ON DELETE CASCADE,
    UNIQUE KEY `uq_user_skill_type` (`user_id`, `skill_id`, `skill_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Skill Exchange Requests Table
CREATE TABLE `skill_exchange_requests` (
    `request_id` INT AUTO_INCREMENT PRIMARY KEY,
    `sender_id` INT NOT NULL,
    `receiver_id` INT NOT NULL,
    `skill_offered` VARCHAR(100) NOT NULL,
    `skill_requested` VARCHAR(100) NOT NULL,
    `message` TEXT,
    `status` ENUM('pending', 'accepted', 'rejected', 'cancelled') DEFAULT 'pending',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_request_sender` FOREIGN KEY (`sender_id`)
        REFERENCES `users`(`user_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_request_receiver` FOREIGN KEY (`receiver_id`)
        REFERENCES `users`(`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Connections Table (Established Peer Partnerships)
CREATE TABLE `connections` (
    `connection_id` INT AUTO_INCREMENT PRIMARY KEY,
    `user1_id` INT NOT NULL,
    `user2_id` INT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_conn_user1` FOREIGN KEY (`user1_id`)
        REFERENCES `users`(`user_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_conn_user2` FOREIGN KEY (`user2_id`)
        REFERENCES `users`(`user_id`) ON DELETE CASCADE,
    UNIQUE KEY `uq_peer_connection` (`user1_id`, `user2_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Messages Table (Chat Module)
CREATE TABLE `messages` (
    `message_id` INT AUTO_INCREMENT PRIMARY KEY,
    `sender_id` INT NOT NULL,
    `receiver_id` INT NOT NULL,
    `message_text` TEXT NOT NULL,
    `is_read` BOOLEAN DEFAULT FALSE,
    `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_msg_sender` FOREIGN KEY (`sender_id`)
        REFERENCES `users`(`user_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_msg_receiver` FOREIGN KEY (`receiver_id`)
        REFERENCES `users`(`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Learning Sessions Table
CREATE TABLE `learning_sessions` (
    `session_id` INT AUTO_INCREMENT PRIMARY KEY,
    `host_id` INT NOT NULL,
    `partner_id` INT NOT NULL,
    `session_title` VARCHAR(150) NOT NULL,
    `skill_name` VARCHAR(100) NOT NULL,
    `session_date` DATE NOT NULL,
    `session_time` TIME NOT NULL,
    `description` TEXT,
    `meeting_link` VARCHAR(255),
    `status` ENUM('upcoming', 'completed', 'cancelled') DEFAULT 'upcoming',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_session_host` FOREIGN KEY (`host_id`)
        REFERENCES `users`(`user_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_session_partner` FOREIGN KEY (`partner_id`)
        REFERENCES `users`(`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Notifications Table
CREATE TABLE `notifications` (
    `notification_id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `message` TEXT NOT NULL,
    `type` VARCHAR(50) DEFAULT 'info',
    `link` VARCHAR(100),
    `is_read` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_notif_user` FOREIGN KEY (`user_id`)
        REFERENCES `users`(`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Indexes for performance
CREATE INDEX `idx_users_email` ON `users`(`email`);
CREATE INDEX `idx_skills_category` ON `skills`(`category`);
CREATE INDEX `idx_requests_status` ON `skill_exchange_requests`(`status`);
CREATE INDEX `idx_messages_pair` ON `messages`(`sender_id`, `receiver_id`);
CREATE INDEX `idx_sessions_status` ON `learning_sessions`(`status`);
CREATE INDEX `idx_notif_user_unread` ON `notifications`(`user_id`, `is_read`);

-- ===================================================================
-- SAMPLE DATA INSERTIONS
-- ===================================================================

-- 1. Master Skills
INSERT INTO `skills` (`skill_id`, `skill_name`, `category`) VALUES
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
(16, 'Public Speaking', 'Soft Skills');

-- 2. Users (Admin + 10 Sample Students)
-- All student passwords are 'password123'
-- Admin password is 'admin123'
INSERT INTO `users` (`user_id`, `full_name`, `email`, `password_hash`, `college_name`, `department`, `year_of_study`, `bio`, `profile_image`, `role`, `status`) VALUES
(1, 'System Administrator', 'admin@skillswap.edu', 'scrypt:32768:8:1$luuNaI6RHI9EH0i3$7ea7d8494fec71116d0a6839c30804612e804cdb64b879fa362fd49e79747353ab909fa46e6a4c5dd92b73a69c5343be102057387ef2dca7c366128ba942cd50', 'SkillSwap University', 'Administration', 'Staff', 'Platform manager maintaining community guidelines and technical stability.', 'default_avatar.png', 'admin', 'active'),

(2, 'Rahul Sharma', 'rahul@college.edu', 'scrypt:32768:8:1$X6EIwKzlz0j82Lmb$ced50e9c8e5ed140e8f2f11f1d1a5c024c0e8af5236c0f275f71fe5564fba2ead515802e1e90bcadd982c25b1030e373bcca2bc18370664e59cfd4a6e87af146', 'National Institute of Technology', 'Computer Science', '3rd Year', 'Experienced Java coder and DSA problem solver. Looking forward to learning Python for ML and scripting.', 'avatar1.png', 'student', 'active'),

(3, 'Priya Patel', 'priya@college.edu', 'scrypt:32768:8:1$X6EIwKzlz0j82Lmb$ced50e9c8e5ed140e8f2f11f1d1a5c024c0e8af5236c0f275f71fe5564fba2ead515802e1e90bcadd982c25b1030e373bcca2bc18370664e59cfd4a6e87af146', 'National Institute of Technology', 'Information Technology', '3rd Year', 'Passionate Python developer building data scripts. Eager to master Java and object-oriented backend patterns.', 'avatar2.png', 'student', 'active'),

(4, 'Kiran Rao', 'kiran@college.edu', 'scrypt:32768:8:1$X6EIwKzlz0j82Lmb$ced50e9c8e5ed140e8f2f11f1d1a5c024c0e8af5236c0f275f71fe5564fba2ead515802e1e90bcadd982c25b1030e373bcca2bc18370664e59cfd4a6e87af146', 'City Engineering College', 'Computer Science', '2nd Year', 'Frontend enthusiast skilled in HTML & CSS responsive layouts. Looking to master modern JavaScript and DOM.', 'avatar3.png', 'student', 'active'),

(5, 'Sita Kumari', 'sita@college.edu', 'scrypt:32768:8:1$X6EIwKzlz0j82Lmb$ced50e9c8e5ed140e8f2f11f1d1a5c024c0e8af5236c0f275f71fe5564fba2ead515802e1e90bcadd982c25b1030e373bcca2bc18370664e59cfd4a6e87af146', 'City Engineering College', 'Computer Science', '2nd Year', 'JavaScript and web logic builder. Want to polish advanced CSS animations and modern layout systems.', 'avatar4.png', 'student', 'active'),

(6, 'Arun Kumar', 'arun@college.edu', 'scrypt:32768:8:1$X6EIwKzlz0j82Lmb$ced50e9c8e5ed140e8f2f11f1d1a5c024c0e8af5236c0f275f71fe5564fba2ead515802e1e90bcadd982c25b1030e373bcca2bc18370664e59cfd4a6e87af146', 'State Technical University', 'Information Science', '4th Year', 'Database administrator skilled in SQL queries, indexing, and joins. Eager to pick up Python fundamentals.', 'avatar5.png', 'student', 'active'),

(7, 'Ananya Iyer', 'ananya@college.edu', 'scrypt:32768:8:1$X6EIwKzlz0j82Lmb$ced50e9c8e5ed140e8f2f11f1d1a5c024c0e8af5236c0f275f71fe5564fba2ead515802e1e90bcadd982c25b1030e373bcca2bc18370664e59cfd4a6e87af146', 'State Technical University', 'Data Science & AI', '3rd Year', 'Python programmer focused on statistical modeling. Seeking deep relational SQL and database optimization skills.', 'avatar6.png', 'student', 'active'),

(8, 'Vikram Singh', 'vikram@college.edu', 'scrypt:32768:8:1$X6EIwKzlz0j82Lmb$ced50e9c8e5ed140e8f2f11f1d1a5c024c0e8af5236c0f275f71fe5564fba2ead515802e1e90bcadd982c25b1030e373bcca2bc18370664e59cfd4a6e87af146', 'Apex School of Technology', 'Digital Media', '3rd Year', 'UI/UX and Graphic Designer proficient in Figma and Canva. Looking to learn HTML & CSS frontend coding.', 'avatar7.png', 'student', 'active'),

(9, 'Neha Gupta', 'neha@college.edu', 'scrypt:32768:8:1$X6EIwKzlz0j82Lmb$ced50e9c8e5ed140e8f2f11f1d1a5c024c0e8af5236c0f275f71fe5564fba2ead515802e1e90bcadd982c25b1030e373bcca2bc18370664e59cfd4a6e87af146', 'Apex School of Technology', 'Computer Science', '3rd Year', 'Frontend web developer creating web interfaces. Want to collaborate with a graphic/UI designer to learn design thinking.', 'avatar8.png', 'student', 'active'),

(10, 'Rohan Verma', 'rohan@college.edu', 'scrypt:32768:8:1$X6EIwKzlz0j82Lmb$ced50e9c8e5ed140e8f2f11f1d1a5c024c0e8af5236c0f275f71fe5564fba2ead515802e1e90bcadd982c25b1030e373bcca2bc18370664e59cfd4a6e87af146', 'Metro Institute of Tech', 'Electronics', '2nd Year', 'C programming and embedded hardware explorer. Interested in learning Python for robotics scripts.', 'avatar9.png', 'student', 'active'),

(11, 'Meera Nambiar', 'meera@college.edu', 'scrypt:32768:8:1$X6EIwKzlz0j82Lmb$ced50e9c8e5ed140e8f2f11f1d1a5c024c0e8af5236c0f275f71fe5564fba2ead515802e1e90bcadd982c25b1030e373bcca2bc18370664e59cfd4a6e87af146', 'Metro Institute of Tech', 'Business Administration', '4th Year', 'Public speaker and campus debate mentor. Wanting to learn Python for business analytics and automation.', 'avatar10.png', 'student', 'active');

-- 3. Student Skills (Teaching & Learning)
-- Rahul (2): Teaches Java(1), Data Structures(4) | Wants Python(2), Machine Learning(11)
-- Priya (3): Teaches Python(2), Machine Learning(11) | Wants Java(1), Data Structures(4)
-- Kiran (4): Teaches HTML & CSS(5) | Wants JavaScript(6), React JS(7)
-- Sita (5): Teaches JavaScript(6), React JS(7) | Wants HTML & CSS(5), Graphic Design(13)
-- Arun (6): Teaches SQL(9) | Wants Python(2), Data Analytics(12)
-- Ananya (7): Teaches Python(2), Data Analytics(12) | Wants SQL(9), MongoDB(10)
-- Vikram (8): Teaches Graphic Design(13), UI/UX Design(14) | Wants HTML & CSS(5), JavaScript(6)
-- Neha (9): Teaches HTML & CSS(5), JavaScript(6) | Wants Graphic Design(13), UI/UX Design(14)
-- Rohan (10): Teaches C Programming(3) | Wants Python(2)
-- Meera (11): Teaches Public Speaking(16), Communication Skills(15) | Wants Python(2)
INSERT INTO `student_skills` (`user_id`, `skill_id`, `skill_type`) VALUES
-- Rahul
(2, 1, 'teach'), (2, 4, 'teach'),
(2, 2, 'learn'), (2, 11, 'learn'),
-- Priya
(3, 2, 'teach'), (3, 11, 'teach'),
(3, 1, 'learn'), (3, 4, 'learn'),
-- Kiran
(4, 5, 'teach'),
(4, 6, 'learn'), (4, 7, 'learn'),
-- Sita
(5, 6, 'teach'), (5, 7, 'teach'),
(5, 5, 'learn'), (5, 13, 'learn'),
-- Arun
(6, 9, 'teach'),
(6, 2, 'learn'), (6, 12, 'learn'),
-- Ananya
(7, 2, 'teach'), (7, 12, 'teach'),
(7, 9, 'learn'), (7, 10, 'learn'),
-- Vikram
(8, 13, 'teach'), (8, 14, 'teach'),
(8, 5, 'learn'), (8, 6, 'learn'),
-- Neha
(9, 5, 'teach'), (9, 6, 'teach'),
(9, 13, 'learn'), (9, 14, 'learn'),
-- Rohan
(10, 3, 'teach'),
(10, 2, 'learn'),
-- Meera
(11, 15, 'teach'), (11, 16, 'teach'),
(11, 2, 'learn');

-- 4. Sample Skill Exchange Requests
INSERT INTO `skill_exchange_requests` (`request_id`, `sender_id`, `receiver_id`, `skill_offered`, `skill_requested`, `message`, `status`, `created_at`) VALUES
(1, 2, 3, 'Java', 'Python', 'Hey Priya, I noticed you are skilled in Python. Would love to teach you Java OOP in exchange for Python data scripting!', 'accepted', DATE_SUB(NOW(), INTERVAL 5 DAY)),
(2, 4, 5, 'HTML & CSS', 'JavaScript', 'Hi Sita! I can help you with modern CSS flex/grid layout if you can mentor me in JavaScript async/await.', 'accepted', DATE_SUB(NOW(), INTERVAL 4 DAY)),
(3, 6, 7, 'SQL', 'Python', 'Hello Ananya! Need assistance in relational query tuning? I want to learn Python pandas from you.', 'accepted', DATE_SUB(NOW(), INTERVAL 3 DAY)),
(4, 8, 9, 'UI/UX Design', 'HTML & CSS', 'Hi Neha! Would love to exchange Figma wireframing for your HTML/CSS coding expertise.', 'pending', DATE_SUB(NOW(), INTERVAL 2 DAY)),
(5, 10, 2, 'C Programming', 'Java', 'Hi Rahul, can we connect? I can teach C pointer fundamentals in exchange for Java help.', 'pending', DATE_SUB(NOW(), INTERVAL 1 DAY)),
(6, 11, 3, 'Public Speaking', 'Python', 'Hello Priya, looking forward to trading interview speech techniques for Python basics.', 'pending', NOW());

-- 5. Sample Connections (Established between accepted request peers)
INSERT INTO `connections` (`connection_id`, `user1_id`, `user2_id`, `created_at`) VALUES
(1, 2, 3, DATE_SUB(NOW(), INTERVAL 5 DAY)),
(2, 4, 5, DATE_SUB(NOW(), INTERVAL 4 DAY)),
(3, 6, 7, DATE_SUB(NOW(), INTERVAL 3 DAY));

-- 6. Sample Chat Messages
INSERT INTO `messages` (`message_id`, `sender_id`, `receiver_id`, `message_text`, `is_read`, `timestamp`) VALUES
(1, 2, 3, 'Hi Priya! Glad to connect on SkillSwap. When are you free for our first Java / Python exchange?', 1, DATE_SUB(NOW(), INTERVAL 4 DAY)),
(2, 3, 2, 'Hey Rahul! Excited to learn Java. I am free this Saturday at 4 PM. We can start with Python basics first!', 1, DATE_SUB(NOW(), INTERVAL 4 DAY)),
(3, 2, 3, 'Sounds great! I scheduled our first session on the Sessions page with a Google Meet link.', 1, DATE_SUB(NOW(), INTERVAL 3 DAY)),
(4, 4, 5, 'Hi Sita, I reviewed your CSS question. Flexbox wrap with gap will solve your layout issue nicely.', 1, DATE_SUB(NOW(), INTERVAL 2 DAY)),
(5, 5, 4, 'Thanks Kiran! That worked perfectly. Let me know when you want to dive into JavaScript DOM events.', 0, DATE_SUB(NOW(), INTERVAL 1 DAY));

-- 7. Sample Learning Sessions
INSERT INTO `learning_sessions` (`session_id`, `host_id`, `partner_id`, `session_title`, `skill_name`, `session_date`, `session_time`, `description`, `meeting_link`, `status`, `created_at`) VALUES
(1, 2, 3, 'Java OOP & Class Design Workshop', 'Java', DATE_ADD(CURRENT_DATE, INTERVAL 2 DAY), '16:00:00', 'Introduction to Java classes, encapsulation, inheritance, and code examples.', 'https://meet.google.com/abc-defg-hij', 'upcoming', NOW()),
(2, 3, 2, 'Python Data Scripting & Pandas Intro', 'Python', DATE_ADD(CURRENT_DATE, INTERVAL 4 DAY), '17:30:00', 'Hands-on session covering Python dictionary comprehension, list slices, and functions.', 'https://meet.google.com/xyz-uvwx-rst', 'upcoming', NOW()),
(3, 4, 5, 'Modern CSS Grid Deep Dive', 'HTML & CSS', DATE_SUB(CURRENT_DATE, INTERVAL 2 DAY), '15:00:00', 'Two-dimensional grid layouts, template areas, and mobile responsiveness.', 'https://meet.google.com/qwe-rtyu-iop', 'completed', DATE_SUB(NOW(), INTERVAL 3 DAY));

-- 8. Sample Notifications
INSERT INTO `notifications` (`notification_id`, `user_id`, `title`, `message`, `type`, `link`, `is_read`, `created_at`) VALUES
(1, 2, 'Exchange Request Accepted', 'Priya Patel accepted your skill exchange proposal for Java ⇄ Python.', 'request', 'requests.html', 1, DATE_SUB(NOW(), INTERVAL 5 DAY)),
(2, 2, 'New Learning Session Scheduled', 'Upcoming session: Java OOP & Class Design Workshop is set for this weekend.', 'session', 'sessions.html', 0, NOW()),
(3, 2, 'New Connection', 'You and Priya Patel are now connected! You can now chat and organize learning sessions.', 'connection', 'chat.html', 1, DATE_SUB(NOW(), INTERVAL 5 DAY)),
(4, 3, 'New Message', 'Rahul Sharma sent you a message: "Sounds great! I scheduled our first session..."', 'message', 'chat.html', 0, DATE_SUB(NOW(), INTERVAL 3 DAY)),
(5, 9, 'New Exchange Request', 'Vikram Singh sent you an exchange request: UI/UX Design for HTML & CSS.', 'request', 'requests.html', 0, DATE_SUB(NOW(), INTERVAL 2 DAY));

