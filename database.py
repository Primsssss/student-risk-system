import sqlite3
from pathlib import Path


# Database file
DATABASE = Path(__file__).parent / "student_risk_system.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = get_db_connection()
    cursor = connection.cursor()

    # =========================
    # USERS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK (
                role IN ('admin', 'professor', 'student')
            ),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =========================
    # PROFESSORS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS professors (
            professor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            employee_number TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE,
            FOREIGN KEY (user_id)
                REFERENCES users(user_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # STUDENTS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            student_number TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE,
            course TEXT,
            year_level INTEGER,
            FOREIGN KEY (user_id)
                REFERENCES users(user_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # COURSES / SUBJECTS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            course_id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT UNIQUE NOT NULL,
            course_title TEXT NOT NULL,
            description TEXT
        )
    """)

    # =========================
    # CLASSES
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            class_id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            professor_id INTEGER NOT NULL,
            section TEXT,
            school_year TEXT,
            semester TEXT,
            FOREIGN KEY (course_id)
                REFERENCES courses(course_id)
                ON DELETE CASCADE,
            FOREIGN KEY (professor_id)
                REFERENCES professors(professor_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # ENROLLMENTS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS enrollments (
            enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(class_id, student_id),
            FOREIGN KEY (class_id)
                REFERENCES classes(class_id)
                ON DELETE CASCADE,
            FOREIGN KEY (student_id)
                REFERENCES students(student_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # GRADING PERIODS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grading_periods (
            period_id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_name TEXT UNIQUE NOT NULL
                CHECK (period_name IN ('Prelim', 'Midterm', 'Finals'))
        )
    """)

    # =========================
    # ATTENDANCE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_id INTEGER NOT NULL,
            class_date DATE NOT NULL,
            status TEXT NOT NULL
                CHECK (status IN ('Present', 'Absent')),
            FOREIGN KEY (enrollment_id)
                REFERENCES enrollments(enrollment_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # STUDY HOURS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_hours (
            study_id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_id INTEGER NOT NULL,
            period_id INTEGER NOT NULL,
            study_date DATE NOT NULL,
            hours REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (enrollment_id)
                REFERENCES enrollments(enrollment_id)
                ON DELETE CASCADE,
            FOREIGN KEY (period_id)
                REFERENCES grading_periods(period_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # QUIZZES
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_id INTEGER NOT NULL,
            period_id INTEGER NOT NULL,
            quiz_name TEXT NOT NULL,
            score REAL NOT NULL,
            total_score REAL NOT NULL,
            quiz_date DATE,
            FOREIGN KEY (enrollment_id)
                REFERENCES enrollments(enrollment_id)
                ON DELETE CASCADE,
            FOREIGN KEY (period_id)
                REFERENCES grading_periods(period_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # ACTIVITIES
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_id INTEGER NOT NULL,
            period_id INTEGER NOT NULL,
            activity_name TEXT NOT NULL,
            score REAL NOT NULL,
            total_score REAL NOT NULL,
            activity_date DATE,
            FOREIGN KEY (enrollment_id)
                REFERENCES enrollments(enrollment_id)
                ON DELETE CASCADE,
            FOREIGN KEY (period_id)
                REFERENCES grading_periods(period_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # EXAMS
    # Exam is optional / nullable
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_id INTEGER NOT NULL,
            period_id INTEGER NOT NULL,
            score REAL,
            total_score REAL,
            exam_date DATE,
            FOREIGN KEY (enrollment_id)
                REFERENCES enrollments(enrollment_id)
                ON DELETE CASCADE,
            FOREIGN KEY (period_id)
                REFERENCES grading_periods(period_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # ACADEMIC FACTORS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS academic_factors (
            factor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_id INTEGER NOT NULL,
            period_id INTEGER NOT NULL,
            attendance_percentage REAL DEFAULT 0,
            study_hours REAL DEFAULT 0,
            quiz_average REAL DEFAULT 0,
            activity_average REAL DEFAULT 0,
            exam_percentage REAL,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(enrollment_id, period_id),
            FOREIGN KEY (enrollment_id)
                REFERENCES enrollments(enrollment_id)
                ON DELETE CASCADE,
            FOREIGN KEY (period_id)
                REFERENCES grading_periods(period_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # PREDICTIONS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_id INTEGER NOT NULL,
            period_id INTEGER NOT NULL,
            risk_level TEXT NOT NULL
                CHECK (risk_level IN ('Low', 'Moderate', 'High')),
            prediction_label TEXT NOT NULL,
            description TEXT,
            feedback TEXT,
            predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (enrollment_id)
                REFERENCES enrollments(enrollment_id)
                ON DELETE CASCADE,
            FOREIGN KEY (period_id)
                REFERENCES grading_periods(period_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # WEAK AREAS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weak_areas (
            weak_area_id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER NOT NULL,
            area_name TEXT NOT NULL,
            reason TEXT,
            FOREIGN KEY (prediction_id)
                REFERENCES predictions(prediction_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # LEARNING MODULES
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_modules (
            module_id INTEGER PRIMARY KEY AUTOINCREMENT,
            professor_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            weak_area TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (professor_id)
                REFERENCES professors(professor_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # MODULE ASSIGNMENTS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS module_assignments (
            assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            prediction_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Not Started'
                CHECK (
                    status IN (
                        'Not Started',
                        'In Progress',
                        'Completed'
                    )
                ),
            progress INTEGER NOT NULL DEFAULT 0,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (module_id)
                REFERENCES learning_modules(module_id)
                ON DELETE CASCADE,
            FOREIGN KEY (student_id)
                REFERENCES students(student_id)
                ON DELETE CASCADE,
            FOREIGN KEY (prediction_id)
                REFERENCES predictions(prediction_id)
                ON DELETE SET NULL
        )
    """)

    # =========================
    # MODULE QUIZZES
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS module_quizzes (
            module_quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            FOREIGN KEY (module_id)
                REFERENCES learning_modules(module_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # MODULE QUIZ RESULTS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS module_quiz_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            score REAL NOT NULL,
            total_questions INTEGER NOT NULL,
            percentage REAL NOT NULL,
            taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assignment_id)
                REFERENCES module_assignments(assignment_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # SYSTEM ACTIVITY LOGS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
                REFERENCES users(user_id)
                ON DELETE SET NULL
        )
    """)

    # =========================
    # DEFAULT GRADING PERIODS
    # =========================
    cursor.execute("""
        INSERT OR IGNORE INTO grading_periods (period_name)
        VALUES ('Prelim')
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO grading_periods (period_name)
        VALUES ('Midterm')
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO grading_periods (period_name)
        VALUES ('Finals')
    """)

    connection.commit()
    connection.close()

    print("Database initialized successfully!")