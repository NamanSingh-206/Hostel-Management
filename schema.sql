-- schema.sql  ← COPY THIS FILE to project root and run: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS hostel_db;
USE hostel_db;

-- Disable foreign key checks for clean setup
SET FOREIGN_KEY_CHECKS = 0;

-- Drop existing tables if any
DROP TABLE IF EXISTS allocations;
DROP TABLE IF EXISTS complaints;
DROP TABLE IF EXISTS fees;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS wardens;

SET FOREIGN_KEY_CHECKS = 1;

-- ── WARDENS ──────────────────────────────────────────────────────────────────
CREATE TABLE wardens (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  username    VARCHAR(50)  UNIQUE NOT NULL,
  password    VARCHAR(200) NOT NULL,
  name        VARCHAR(100) NOT NULL,
  email       VARCHAR(100)
);

-- ── ROOMS ─────────────────────────────────────────────────────────────────────
CREATE TABLE rooms (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  room_number VARCHAR(10)  UNIQUE NOT NULL,
  floor       INT          NOT NULL,
  capacity    INT          DEFAULT 2,
  occupied    INT          DEFAULT 0,
  room_type   ENUM('single','double','triple') DEFAULT 'double',
  status      ENUM('available','full','maintenance') DEFAULT 'available'
);

-- ── STUDENTS ──────────────────────────────────────────────────────────────────
CREATE TABLE students (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(100) NOT NULL,
  usn          VARCHAR(20)  UNIQUE NOT NULL,
  email        VARCHAR(100),
  phone        VARCHAR(10)  NOT NULL,
  course       VARCHAR(50),
  year         INT,
  room_id      INT,
  password     VARCHAR(200) DEFAULT NULL,
  joining_date DATE         DEFAULT (CURRENT_DATE),
  status       ENUM('active','inactive') DEFAULT 'active',
  FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL
);

-- ── ALLOCATIONS ───────────────────────────────────────────────────────────────
CREATE TABLE allocations (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  student_id   INT  NOT NULL,
  room_id      INT  NOT NULL,
  allocated_on DATE DEFAULT (CURRENT_DATE),
  vacated_on   DATE,
  FOREIGN KEY (student_id) REFERENCES students(id),
  FOREIGN KEY (room_id)    REFERENCES rooms(id)
);

-- ── FEES ──────────────────────────────────────────────────────────────────────
CREATE TABLE fees (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  student_id  INT            NOT NULL,
  amount      DECIMAL(10,2)  NOT NULL,
  fee_type    ENUM('monthly','yearly','security') DEFAULT 'monthly',
  paid_date   DATE,
  due_date    DATE           NOT NULL,
  status      ENUM('paid','pending','overdue')    DEFAULT 'pending',
  FOREIGN KEY (student_id) REFERENCES students(id)
);

-- ── COMPLAINTS ────────────────────────────────────────────────────────────────
CREATE TABLE complaints (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  student_id  INT  NOT NULL,
  category    ENUM('maintenance','food','security','other') DEFAULT 'other',
  description TEXT NOT NULL,
  filed_on    DATETIME DEFAULT CURRENT_TIMESTAMP,
  status      ENUM('open','in-progress','resolved')        DEFAULT 'open',
  FOREIGN KEY (student_id) REFERENCES students(id)
);

-- ── DEFAULT WARDEN (password will be set by run_once.py) ─────────────────────
INSERT INTO wardens (username, password, name, email)
VALUES ('admin', 'changeme', 'Admin Warden', 'admin@hostel.com');

-- ── SAMPLE ROOMS ──────────────────────────────────────────────────────────────
INSERT INTO rooms (room_number, floor, capacity, room_type, status) VALUES
('101', 1, 2, 'double',  'available'),
('102', 1, 2, 'double',  'available'),
('103', 1, 3, 'triple',  'available'),
('104', 1, 1, 'single',  'available'),
('201', 2, 2, 'double',  'available'),
('202', 2, 2, 'double',  'available'),
('203', 2, 3, 'triple',  'available'),
('204', 2, 1, 'single',  'available'),
('301', 3, 2, 'double',  'available'),
('302', 3, 2, 'double',  'available'),
('303', 3, 3, 'triple',  'available'),
('304', 3, 1, 'single',  'available'),
('401', 4, 2, 'double',  'available'),
('402', 4, 2, 'double',  'available'),
('403', 4, 3, 'triple',  'available'),
('404', 4, 1, 'single',  'available');
