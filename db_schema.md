# Database Schema

```sql
CREATE TABLE users (
	id INTEGER NOT NULL, 
	employee_id VARCHAR NOT NULL, 
	first_name VARCHAR NOT NULL, 
	last_name VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	phone VARCHAR, 
	department VARCHAR, 
	semester INTEGER, 
	hashed_password VARCHAR NOT NULL, 
	role VARCHAR(7) NOT NULL, 
	is_active BOOLEAN, 
	is_deleted BOOLEAN, 
	has_face_data BOOLEAN, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	updated_at DATETIME, program VARCHAR, major VARCHAR, specialization VARCHAR, section VARCHAR, 
	PRIMARY KEY (id)
);

CREATE TABLE academic_sessions (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	start_date DATE NOT NULL, 
	end_date DATE NOT NULL, 
	is_active BOOLEAN, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE attendance (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	entry_type VARCHAR(9) NOT NULL, 
	timestamp DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	confidence_score FLOAT, 
	image_url VARCHAR, 
	is_verified BOOLEAN, 
	is_late BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE face_data (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	encoding TEXT NOT NULL, 
	image_path VARCHAR, 
	face_quality FLOAT, 
	is_verified BOOLEAN, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE attendance_reports (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	check_in_time DATETIME, 
	check_out_time DATETIME, 
	total_hours FLOAT, 
	status VARCHAR(8), 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_date UNIQUE (user_id, date), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE subjects (
	id INTEGER NOT NULL, 
	code VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	department VARCHAR, 
	semester INTEGER, 
	total_classes INTEGER, 
	faculty_id INTEGER, 
	session_id INTEGER, 
	attendance_threshold FLOAT, 
	is_deleted BOOLEAN, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	PRIMARY KEY (id), 
	FOREIGN KEY(faculty_id) REFERENCES users (id), 
	FOREIGN KEY(session_id) REFERENCES academic_sessions (id)
);

CREATE TABLE audit_logs (
	id INTEGER NOT NULL, 
	action VARCHAR(17) NOT NULL, 
	performed_by INTEGER, 
	actor_email VARCHAR, 
	target_user_id INTEGER, 
	target_type VARCHAR, 
	target_id INTEGER, 
	old_value TEXT, 
	new_value TEXT, 
	description TEXT, 
	ip_address VARCHAR, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	PRIMARY KEY (id), 
	FOREIGN KEY(performed_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE subject_enrollments (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	subject_id INTEGER NOT NULL, 
	enrolled_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_student_subject UNIQUE (student_id, subject_id), 
	FOREIGN KEY(student_id) REFERENCES users (id), 
	FOREIGN KEY(subject_id) REFERENCES subjects (id)
);

CREATE TABLE subject_attendance (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	subject_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	status VARCHAR(7), 
	face_verified BOOLEAN, 
	faculty_marked BOOLEAN, 
	final_status VARCHAR(8), 
	resolved_by INTEGER, 
	is_locked BOOLEAN, 
	marked_by INTEGER, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_student_subject_date UNIQUE (student_id, subject_id, date), 
	FOREIGN KEY(student_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE CASCADE, 
	FOREIGN KEY(resolved_by) REFERENCES users (id), 
	FOREIGN KEY(marked_by) REFERENCES users (id)
);

CREATE TABLE class_schedules (
	id INTEGER NOT NULL, 
	subject_id INTEGER NOT NULL, 
	day_of_week INTEGER NOT NULL, 
	start_time TIME NOT NULL, 
	end_time TIME NOT NULL, 
	room VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE CASCADE
);

CREATE TABLE leave_requests (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	subject_id INTEGER NOT NULL, 
	leave_date DATE NOT NULL, 
	leave_type VARCHAR(8), 
	reason TEXT NOT NULL, 
	status VARCHAR(8), 
	approved_by INTEGER, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE CASCADE, 
	FOREIGN KEY(approved_by) REFERENCES users (id)
);

CREATE TABLE attendance_notifications (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	subject_attendance_id INTEGER, 
	subject_id INTEGER NOT NULL, 
	type VARCHAR(12) NOT NULL, 
	message VARCHAR NOT NULL, 
	is_read BOOLEAN, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(subject_attendance_id) REFERENCES subject_attendance (id) ON DELETE CASCADE, 
	FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE CASCADE
);
```
