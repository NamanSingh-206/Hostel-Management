CREATE DATABASE IF NOT EXISTS hostel_db;
USE hostel_db;

CREATE TABLE wardens (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password VARCHAR(200) NOT NULL,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100)
);

CREATE TABLE rooms (
  id INT AUTO_INCREMENT PRIMARY KEY,
  room_number VARCHAR(10) UNIQUE NOT NULL,
  floor INT NOT NULL,
  capacity INT DEFAULT 2,
  occupied INT DEFAULT 0,
  room_type ENUM('single','double','triple') DEFAULT 'double',
  status ENUM('available','full','maintenance') DEFAULT 'available'
);

CREATE TABLE students (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  roll_number VARCHAR(20) UNIQUE NOT NULL,
  email VARCHAR(100),
  phone VARCHAR(15),
  course VARCHAR(50),
  year INT,
  room_id INT,
  joining_date DATE DEFAULT (CURRENT_DATE),
  status ENUM('active','inactive') DEFAULT 'active',
  FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL
);

CREATE TABLE allocations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  room_id INT NOT NULL,
  allocated_on DATE DEFAULT (CURRENT_DATE),
  vacated_on DATE,
  FOREIGN KEY (student_id) REFERENCES students(id),
  FOREIGN KEY (room_id) REFERENCES rooms(id)
);

CREATE TABLE fees (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  fee_type ENUM('monthly','yearly','security') DEFAULT 'monthly',
  paid_date DATE,
  due_date DATE NOT NULL,
  status ENUM('paid','pending','overdue') DEFAULT 'pending',
  FOREIGN KEY (student_id) REFERENCES students(id)
);

CREATE TABLE complaints (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  category ENUM('maintenance','food','security','other') DEFAULT 'other',
  description TEXT NOT NULL,
  filed_on DATETIME DEFAULT CURRENT_TIMESTAMP,
  status ENUM('open','in-progress','resolved') DEFAULT 'open',
  FOREIGN KEY (student_id) REFERENCES students(id)
);

-- Insert a default warden (password: admin123)
INSERT INTO wardens (username, password, name, email)
VALUES ('admin', 'pbkdf2:sha256:600000$salt$hash', 'Admin Warden', 'admin@hostel.com');