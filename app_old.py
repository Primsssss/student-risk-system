from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database import init_db, get_db_connection

from ml_model import analyze_student

app = Flask(__name__)

app.secret_key = "student-risk-system-secret-key"

# Initialize database
init_db()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return redirect(url_for("login"))


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = get_db_connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT *
                FROM users
                WHERE username = ?
            """, (username,))

            user = cursor.fetchone()

        finally:
            connection.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template("login.html")


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    role = session["role"]

    # =====================================================
    # ADMIN DASHBOARD
    # =====================================================

    if role == "admin":

        connection = get_db_connection()

        try:
            cursor = connection.cursor()

            # Professors
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM professors
            """)

            professor_count = cursor.fetchone()["total"]

            # Students
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM students
            """)

            student_count = cursor.fetchone()["total"]

            # Courses
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM courses
            """)

            course_count = cursor.fetchone()["total"]

            # Predictions
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM predictions
            """)

            prediction_count = cursor.fetchone()["total"]

            # Low Risk
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM predictions
                WHERE risk_level = 'Low'
            """)

            low_risk = cursor.fetchone()["total"]

            # Moderate Risk
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM predictions
                WHERE risk_level = 'Moderate'
            """)

            moderate_risk = cursor.fetchone()["total"]

            # High Risk
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM predictions
                WHERE risk_level = 'High'
            """)

            high_risk = cursor.fetchone()["total"]

            # Recent Predictions
            cursor.execute("""
                SELECT
                    predictions.prediction_id,
                    predictions.risk_level,
                    predictions.predicted_at,
                    students.first_name,
                    students.last_name
                FROM predictions

                JOIN enrollments
                    ON predictions.enrollment_id =
                       enrollments.enrollment_id

                JOIN students
                    ON enrollments.student_id =
                       students.student_id

                ORDER BY predictions.predicted_at DESC

                LIMIT 5
            """)

            recent_predictions = cursor.fetchall()

        finally:
            connection.close()

        return render_template(
            "admin_dashboard.html",

            professor_count=professor_count,
            student_count=student_count,
            course_count=course_count,
            prediction_count=prediction_count,

            low_risk=low_risk,
            moderate_risk=moderate_risk,
            high_risk=high_risk,

            recent_predictions=recent_predictions
        )

    # =====================================================
    # PROFESSOR DASHBOARD
    # =====================================================

    elif role == "professor":

        connection = get_db_connection()

        try:
            cursor = connection.cursor()

            # Get the professor profile linked to the logged-in user.
            cursor.execute("""
                SELECT
                    professor_id,
                    user_id,
                    employee_number,
                    first_name,
                    last_name,
                    email
                FROM professors
                WHERE user_id = ?
            """, (session["user_id"],))

            professor = cursor.fetchone()

            if not professor:
                return "Professor profile not found.", 404

            professor_id = professor["professor_id"]

            # Count students enrolled in this professor's classes.
            cursor.execute("""
                SELECT COUNT(DISTINCT e.student_id) AS total
                FROM enrollments e
                JOIN classes c
                    ON e.class_id = c.class_id
                WHERE c.professor_id = ?
            """, (professor_id,))

            student_count = cursor.fetchone()["total"]

            # Count classes handled by this professor.
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM classes
                WHERE professor_id = ?
            """, (professor_id,))

            class_count = cursor.fetchone()["total"]

            # Count predictions belonging to this professor's classes.
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM predictions p
                JOIN enrollments e
                    ON p.enrollment_id = e.enrollment_id
                JOIN classes c
                    ON e.class_id = c.class_id
                WHERE c.professor_id = ?
            """, (professor_id,))

            prediction_count = cursor.fetchone()["total"]

            # Risk distribution for this professor's students.
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM predictions p
                JOIN enrollments e
                    ON p.enrollment_id = e.enrollment_id
                JOIN classes c
                    ON e.class_id = c.class_id
                WHERE c.professor_id = ?
                  AND p.risk_level = 'Low'
            """, (professor_id,))

            low_risk = cursor.fetchone()["total"]

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM predictions p
                JOIN enrollments e
                    ON p.enrollment_id = e.enrollment_id
                JOIN classes c
                    ON e.class_id = c.class_id
                WHERE c.professor_id = ?
                  AND p.risk_level = 'Moderate'
            """, (professor_id,))

            moderate_risk = cursor.fetchone()["total"]

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM predictions p
                JOIN enrollments e
                    ON p.enrollment_id = e.enrollment_id
                JOIN classes c
                    ON e.class_id = c.class_id
                WHERE c.professor_id = ?
                  AND p.risk_level = 'High'
            """, (professor_id,))

            high_risk = cursor.fetchone()["total"]

            at_risk_count = moderate_risk + high_risk

            # Latest predictions for this professor's classes.
            cursor.execute("""
                SELECT
                    p.prediction_id,
                    p.risk_level,
                    p.predicted_at,
                    s.first_name,
                    s.last_name
                FROM predictions p
                JOIN enrollments e
                    ON p.enrollment_id = e.enrollment_id
                JOIN students s
                    ON e.student_id = s.student_id
                JOIN classes c
                    ON e.class_id = c.class_id
                WHERE c.professor_id = ?
                ORDER BY p.predicted_at DESC
                LIMIT 5
            """, (professor_id,))

            recent_predictions = cursor.fetchall()

        finally:
            connection.close()

        return render_template(
            "professor_dashboard.html",
            professor=professor,
            student_count=student_count,
            class_count=class_count,
            prediction_count=prediction_count,
            at_risk_count=at_risk_count,
            low_risk=low_risk,
            moderate_risk=moderate_risk,
            high_risk=high_risk,
            recent_predictions=recent_predictions
        )

    # =====================================================
    # STUDENT DASHBOARD
    # =====================================================

    elif role == "student":

        return """
        <h1>Student Dashboard</h1>
        <p>Student dashboard coming next.</p>
        <a href="/logout">Logout</a>
        """

    return redirect(url_for("login"))


# =========================================================
# PROFESSORS - LIST
# =========================================================

@app.route("/professors")
def professors():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                professors.professor_id,
                professors.employee_number,
                professors.first_name,
                professors.last_name,
                professors.email,
                users.username
            FROM professors

            LEFT JOIN users
                ON professors.user_id = users.user_id

            ORDER BY professors.last_name,
                     professors.first_name
        """)

        professors_list = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "professors.html",
        professors=professors_list
    )


# =========================================================
# ADD PROFESSOR
# =========================================================

@app.route("/professors/add", methods=["GET", "POST"])
def add_professor():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        employee_number = request.form.get(
            "employee_number", ""
        ).strip()

        first_name = request.form.get(
            "first_name", ""
        ).strip()

        last_name = request.form.get(
            "last_name", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip()

        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get(
            "password", ""
        )

        # Required fields
        if not employee_number or not first_name \
                or not last_name or not username or not password:

            return render_template(
                "add_professor.html",
                error="Please complete all required fields."
            )

        connection = get_db_connection()

        try:

            cursor = connection.cursor()

            # Check employee number
            cursor.execute("""
                SELECT professor_id
                FROM professors
                WHERE employee_number = ?
            """, (employee_number,))

            if cursor.fetchone():

                return render_template(
                    "add_professor.html",
                    error="Employee number already exists."
                )

            # Check username
            cursor.execute("""
                SELECT user_id
                FROM users
                WHERE username = ?
            """, (username,))

            if cursor.fetchone():

                return render_template(
                    "add_professor.html",
                    error="Username already exists."
                )

            # Check email
            if email:

                cursor.execute("""
                    SELECT professor_id
                    FROM professors
                    WHERE email = ?
                """, (email,))

                if cursor.fetchone():

                    return render_template(
                        "add_professor.html",
                        error="Email already exists."
                    )

            # Create hashed password
            hashed_password = generate_password_hash(password)

            # Create user account
            cursor.execute("""
                INSERT INTO users
                (
                    username,
                    password,
                    role
                )
                VALUES (?, ?, 'professor')
            """, (
                username,
                hashed_password
            ))

            user_id = cursor.lastrowid

            # Create professor record
            cursor.execute("""
                INSERT INTO professors
                (
                    user_id,
                    employee_number,
                    first_name,
                    last_name,
                    email
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                employee_number,
                first_name,
                last_name,
                email if email else None
            ))

            connection.commit()

        except Exception as e:

            connection.rollback()

            return render_template(
                "add_professor.html",
                error=f"Unable to create professor: {e}"
            )

        finally:
            connection.close()

        return redirect(url_for("professors"))

    return render_template("add_professor.html")


# =========================================================
# EDIT PROFESSOR
# =========================================================

@app.route(
    "/professors/edit/<int:professor_id>",
    methods=["GET", "POST"]
)
def edit_professor(professor_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                professors.*,
                users.username
            FROM professors

            LEFT JOIN users
                ON professors.user_id = users.user_id

            WHERE professors.professor_id = ?
        """, (professor_id,))

        professor = cursor.fetchone()

        if not professor:

            return "Professor not found.", 404

        if request.method == "POST":

            employee_number = request.form.get(
                "employee_number", ""
            ).strip()

            first_name = request.form.get(
                "first_name", ""
            ).strip()

            last_name = request.form.get(
                "last_name", ""
            ).strip()

            email = request.form.get(
                "email", ""
            ).strip()

            if not employee_number or not first_name \
                    or not last_name:

                return render_template(
                    "edit_professor.html",
                    professor=professor,
                    error="Please complete all required fields."
                )

            # Check duplicate employee number
            cursor.execute("""
                SELECT professor_id
                FROM professors
                WHERE employee_number = ?
                AND professor_id != ?
            """, (
                employee_number,
                professor_id
            ))

            if cursor.fetchone():

                return render_template(
                    "edit_professor.html",
                    professor=professor,
                    error="Employee number already exists."
                )

            # Check duplicate email
            if email:

                cursor.execute("""
                    SELECT professor_id
                    FROM professors
                    WHERE email = ?
                    AND professor_id != ?
                """, (
                    email,
                    professor_id
                ))

                if cursor.fetchone():

                    return render_template(
                        "edit_professor.html",
                        professor=professor,
                        error="Email already exists."
                    )

            # Update professor
            cursor.execute("""
                UPDATE professors

                SET
                    employee_number = ?,
                    first_name = ?,
                    last_name = ?,
                    email = ?

                WHERE professor_id = ?
            """, (
                employee_number,
                first_name,
                last_name,
                email if email else None,
                professor_id
            ))

            connection.commit()

            return redirect(url_for("professors"))

        return render_template(
            "edit_professor.html",
            professor=professor
        )

    finally:
        connection.close()


# =========================================================
# DELETE PROFESSOR
# =========================================================

@app.route(
    "/professors/delete/<int:professor_id>",
    methods=["POST"]
)
def delete_professor(professor_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:

        cursor = connection.cursor()

        # Get linked user
        cursor.execute("""
            SELECT user_id
            FROM professors
            WHERE professor_id = ?
        """, (professor_id,))

        professor = cursor.fetchone()

        if professor:

            user_id = professor["user_id"]

            # Delete the professor record first.
            cursor.execute("""
                DELETE FROM professors
                WHERE professor_id = ?
            """, (professor_id,))

            # Delete the linked login account.
            if user_id:
                cursor.execute("""
                    DELETE FROM users
                    WHERE user_id = ?
                """, (user_id,))

            connection.commit()

    except Exception as e:

        connection.rollback()
        return f"Unable to delete professor: {e}", 500

    finally:
        connection.close()

    return redirect(url_for("professors"))


# =========================================================
# COURSES - LIST
# =========================================================

@app.route("/courses")
def courses():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                c.course_id,
                c.course_code,
                c.course_title,
                c.description,
                COUNT(DISTINCT cl.class_id) AS class_count
            FROM courses c
            LEFT JOIN classes cl
                ON c.course_id = cl.course_id
            GROUP BY
                c.course_id,
                c.course_code,
                c.course_title,
                c.description
            ORDER BY c.course_code
        """)

        courses_list = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "courses.html",
        courses=courses_list
    )


# =========================================================
# ADD COURSE
# =========================================================

@app.route("/courses/add", methods=["GET", "POST"])
def add_course():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        course_code = request.form.get(
            "course_code", ""
        ).strip().upper()

        course_title = request.form.get(
            "course_title", ""
        ).strip()

        description = request.form.get(
            "description", ""
        ).strip()

        if not course_code or not course_title:

            return render_template(
                "add_course.html",
                error="Course code and course title are required.",
                course_code=course_code,
                course_title=course_title,
                description=description
            )

        connection = get_db_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT course_id
                FROM courses
                WHERE course_code = ?
            """, (course_code,))

            if cursor.fetchone():

                return render_template(
                    "add_course.html",
                    error="Course code already exists.",
                    course_code=course_code,
                    course_title=course_title,
                    description=description
                )

            cursor.execute("""
                INSERT INTO courses
                (
                    course_code,
                    course_title,
                    description
                )
                VALUES (?, ?, ?)
            """, (
                course_code,
                course_title,
                description if description else None
            ))

            connection.commit()

        except Exception as e:

            connection.rollback()

            return render_template(
                "add_course.html",
                error=f"Unable to create course: {e}",
                course_code=course_code,
                course_title=course_title,
                description=description
            )

        finally:
            connection.close()

        return redirect(url_for("courses"))

    return render_template("add_course.html")


# =========================================================
# EDIT COURSE
# =========================================================

@app.route("/courses/edit/<int:course_id>", methods=["GET", "POST"])
def edit_course(course_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                course_id,
                course_code,
                course_title,
                description
            FROM courses
            WHERE course_id = ?
        """, (course_id,))

        course = cursor.fetchone()

        if not course:
            return "Course not found.", 404

        if request.method == "POST":

            course_code = request.form.get(
                "course_code", ""
            ).strip().upper()

            course_title = request.form.get(
                "course_title", ""
            ).strip()

            description = request.form.get(
                "description", ""
            ).strip()

            if not course_code or not course_title:

                return render_template(
                    "edit_course.html",
                    course=course,
                    error="Course code and course title are required."
                )

            cursor.execute("""
                SELECT course_id
                FROM courses
                WHERE course_code = ?
                  AND course_id != ?
            """, (
                course_code,
                course_id
            ))

            if cursor.fetchone():

                return render_template(
                    "edit_course.html",
                    course=course,
                    error="Course code already exists."
                )

            cursor.execute("""
                UPDATE courses

                SET
                    course_code = ?,
                    course_title = ?,
                    description = ?

                WHERE course_id = ?
            """, (
                course_code,
                course_title,
                description if description else None,
                course_id
            ))

            connection.commit()

            return redirect(url_for("courses"))

        return render_template(
            "edit_course.html",
            course=course
        )

    finally:
        connection.close()


# =========================================================
# DELETE COURSE
# =========================================================

@app.route("/courses/delete/<int:course_id>", methods=["POST"])
def delete_course(course_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT course_id
            FROM courses
            WHERE course_id = ?
        """, (course_id,))

        course = cursor.fetchone()

        if not course:
            return "Course not found.", 404

        # Do not silently delete classes, enrollments,
        # academic records, and predictions through CASCADE.
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM classes
            WHERE course_id = ?
        """, (course_id,))

        class_count = cursor.fetchone()["total"]

        if class_count > 0:

            return render_template(
                "courses.html",
                courses=_get_courses_for_page(connection),
                error=(
                    "This course cannot be deleted because it is "
                    "already assigned to one or more classes. "
                    "Delete or reassign those classes first."
                )
            )

        cursor.execute("""
            DELETE FROM courses
            WHERE course_id = ?
        """, (course_id,))

        connection.commit()

    except Exception as e:

        connection.rollback()

        return f"Unable to delete course: {e}", 500

    finally:
        connection.close()

    return redirect(url_for("courses"))


def _get_courses_for_page(connection):

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            c.course_id,
            c.course_code,
            c.course_title,
            c.description,
            COUNT(DISTINCT cl.class_id) AS class_count
        FROM courses c
        LEFT JOIN classes cl
            ON c.course_id = cl.course_id
        GROUP BY
            c.course_id,
            c.course_code,
            c.course_title,
            c.description
        ORDER BY c.course_code
    """)

    return cursor.fetchall()
# =========================================================
# CLASSES - LIST
# =========================================================

@app.route("/classes")
def classes():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                cl.class_id,
                cl.section,
                cl.school_year,
                cl.semester,
                c.course_id,
                c.course_code,
                c.course_title,
                p.professor_id,
                p.first_name AS professor_first_name,
                p.last_name AS professor_last_name,
                COUNT(DISTINCT e.student_id) AS student_count
            FROM classes cl

            JOIN courses c
                ON cl.course_id = c.course_id

            JOIN professors p
                ON cl.professor_id = p.professor_id

            LEFT JOIN enrollments e
                ON cl.class_id = e.class_id

            GROUP BY
                cl.class_id,
                cl.section,
                cl.school_year,
                cl.semester,
                c.course_id,
                c.course_code,
                c.course_title,
                p.professor_id,
                p.first_name,
                p.last_name

            ORDER BY c.course_code, cl.section
        """)

        classes_list = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "classes.html",
        classes=classes_list
    )


# =========================================================
# ADD CLASS
# =========================================================

# =========================================================
# ADD CLASS
# =========================================================

@app.route("/classes/add", methods=["GET", "POST"])
def add_class():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:

        cursor = connection.cursor()

        # Get courses
        cursor.execute("""
            SELECT
                course_id,
                course_code,
                course_title
            FROM courses
            ORDER BY course_code
        """)

        courses_list = cursor.fetchall()

        # Get professors
        cursor.execute("""
            SELECT
                professor_id,
                employee_number,
                first_name,
                last_name
            FROM professors
            ORDER BY last_name, first_name
        """)

        professors_list = cursor.fetchall()

        # =====================================================
        # PROCESS FORM
        # =====================================================

        if request.method == "POST":

            course_id = request.form.get(
                "course_id", ""
            ).strip()

            professor_id = request.form.get(
                "professor_id", ""
            ).strip()

            section = request.form.get(
                "section", ""
            ).strip()

            school_year = request.form.get(
                "school_year", ""
            ).strip()

            semester = request.form.get(
                "semester", ""
            ).strip()

            # Required fields
            if not course_id or not professor_id:

                return render_template(
                    "add_class.html",
                    courses=courses_list,
                    professors=professors_list,
                    error="Please select a course and professor."
                )

            # =================================================
            # CHECK DUPLICATE CLASS
            # =================================================

            cursor.execute("""
                SELECT class_id
                FROM classes
                WHERE course_id = ?
                  AND professor_id = ?
                  AND section = ?
                  AND school_year = ?
                  AND semester = ?
            """, (
                int(course_id),
                int(professor_id),
                section if section else None,
                school_year if school_year else None,
                semester if semester else None
            ))

            if cursor.fetchone():

                return render_template(
                    "add_class.html",
                    courses=courses_list,
                    professors=professors_list,
                    error="This class already exists."
                )

            # =================================================
            # CREATE CLASS
            # =================================================

            cursor.execute("""
                INSERT INTO classes
                (
                    course_id,
                    professor_id,
                    section,
                    school_year,
                    semester
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                int(course_id),
                int(professor_id),
                section if section else None,
                school_year if school_year else None,
                semester if semester else None
            ))

            connection.commit()

            return redirect(url_for("classes"))

        # =====================================================
        # SHOW ADD CLASS FORM
        # =====================================================

        return render_template(
            "add_class.html",
            courses=courses_list,
            professors=professors_list
        )

    except Exception as e:

        connection.rollback()

        return render_template(
            "add_class.html",
            courses=courses_list,
            professors=professors_list,
            error=f"Unable to create class: {e}"
        )

    finally:

        connection.close()


# =========================================================
# EDIT CLASS
# =========================================================

@app.route("/classes/edit/<int:class_id>", methods=["GET", "POST"])
def edit_class(class_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM classes
            WHERE class_id = ?
        """, (class_id,))

        class_record = cursor.fetchone()

        if not class_record:
            return "Class not found.", 404

        cursor.execute("""
            SELECT
                course_id,
                course_code,
                course_title
            FROM courses
            ORDER BY course_code
        """)

        courses_list = cursor.fetchall()

        cursor.execute("""
            SELECT
                professor_id,
                employee_number,
                first_name,
                last_name
            FROM professors
            ORDER BY last_name, first_name
        """)

        professors_list = cursor.fetchall()

        if request.method == "POST":

            course_id = request.form.get("course_id", "").strip()
            professor_id = request.form.get("professor_id", "").strip()
            section = request.form.get("section", "").strip()
            school_year = request.form.get("school_year", "").strip()
            semester = request.form.get("semester", "").strip()

            if not course_id or not professor_id:

                return render_template(
                    "edit_class.html",
                    class_record=class_record,
                    courses=courses_list,
                    professors=professors_list,
                    error="Please select a course and professor."
                )

            # Check duplicate
            cursor.execute("""
                SELECT class_id
                FROM classes
                WHERE course_id = ?
                  AND professor_id = ?
                  AND section = ?
                  AND school_year = ?
                  AND semester = ?
                  AND class_id != ?
            """, (
                course_id,
                professor_id,
                section if section else None,
                school_year if school_year else None,
                semester if semester else None,
                class_id
            ))

            if cursor.fetchone():

                return render_template(
                    "edit_class.html",
                    class_record=class_record,
                    courses=courses_list,
                    professors=professors_list,
                    error="This class already exists."
                )

            cursor.execute("""
                UPDATE classes
                SET
                    course_id = ?,
                    professor_id = ?,
                    section = ?,
                    school_year = ?,
                    semester = ?
                WHERE class_id = ?
            """, (
                int(course_id),
                int(professor_id),
                section if section else None,
                school_year if school_year else None,
                semester if semester else None,
                class_id
            ))

            connection.commit()

            return redirect(url_for("classes"))

        return render_template(
            "edit_class.html",
            class_record=class_record,
            courses=courses_list,
            professors=professors_list
        )

    finally:
        connection.close()


# =========================================================
# DELETE CLASS
# =========================================================

@app.route("/classes/delete/<int:class_id>", methods=["POST"])
def delete_class(class_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT class_id
            FROM classes
            WHERE class_id = ?
        """, (class_id,))

        class_record = cursor.fetchone()

        if not class_record:
            return "Class not found.", 404

        # Check enrollments first
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM enrollments
            WHERE class_id = ?
        """, (class_id,))

        enrollment_count = cursor.fetchone()["total"]

        if enrollment_count > 0:
            return (
                "This class cannot be deleted because students "
                "are already enrolled in it. Remove the enrollments first."
            ), 400

        cursor.execute("""
            DELETE FROM classes
            WHERE class_id = ?
        """, (class_id,))

        connection.commit()

    except Exception as e:

        connection.rollback()

        return f"Unable to delete class: {e}", 500

    finally:
        connection.close()

    return redirect(url_for("classes"))
# =========================================================
# STUDENTS
# =========================================================

@app.route("/students")
def students():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                student_id,
                student_number,
                first_name,
                last_name,
                email,
                course,
                year_level
            FROM students
            ORDER BY last_name, first_name
        """)

        students_list = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "students.html",
        students=students_list
    )


# =========================================================
# ADD STUDENT
# =========================================================

@app.route("/students/add", methods=["GET", "POST"])
def add_student():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        student_number = request.form.get(
            "student_number", ""
        ).strip()

        first_name = request.form.get(
            "first_name", ""
        ).strip()

        last_name = request.form.get(
            "last_name", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip()

        course = request.form.get(
            "course", ""
        ).strip()

        year_level = request.form.get(
            "year_level", ""
        ).strip()

        if not student_number or not first_name or not last_name:

            return render_template(
                "add_student.html",
                error="Please complete all required fields."
            )

        connection = get_db_connection()

        try:

            cursor = connection.cursor()

            # Check duplicate student number
            cursor.execute("""
                SELECT student_id
                FROM students
                WHERE student_number = ?
            """, (student_number,))

            if cursor.fetchone():

                return render_template(
                    "add_student.html",
                    error="Student number already exists."
                )

            # Check duplicate email
            if email:

                cursor.execute("""
                    SELECT student_id
                    FROM students
                    WHERE email = ?
                """, (email,))

                if cursor.fetchone():

                    return render_template(
                        "add_student.html",
                        error="Email already exists."
                    )

            # Create student
            cursor.execute("""
                INSERT INTO students
                (
                    student_number,
                    first_name,
                    last_name,
                    email,
                    course,
                    year_level
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                student_number,
                first_name,
                last_name,
                email if email else None,
                course if course else None,
                int(year_level) if year_level else None
            ))

            connection.commit()

        except Exception as e:

            connection.rollback()

            return render_template(
                "add_student.html",
                error=f"Unable to create student: {e}"
            )

        finally:
            connection.close()

        return redirect(url_for("students"))

    return render_template("add_student.html")


# =========================================================
# EDIT STUDENT
# =========================================================

@app.route(
    "/students/edit/<int:student_id>",
    methods=["GET", "POST"]
)
def edit_student(student_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM students
            WHERE student_id = ?
        """, (student_id,))

        student = cursor.fetchone()

        if not student:
            return "Student not found.", 404

        if request.method == "POST":

            student_number = request.form.get(
                "student_number", ""
            ).strip()

            first_name = request.form.get(
                "first_name", ""
            ).strip()

            last_name = request.form.get(
                "last_name", ""
            ).strip()

            email = request.form.get(
                "email", ""
            ).strip()

            course = request.form.get(
                "course", ""
            ).strip()

            year_level = request.form.get(
                "year_level", ""
            ).strip()

            if not student_number or not first_name or not last_name:

                return render_template(
                    "edit_student.html",
                    student=student,
                    error="Please complete all required fields."
                )

            cursor.execute("""
                SELECT student_id
                FROM students
                WHERE student_number = ?
                  AND student_id != ?
            """, (
                student_number,
                student_id
            ))

            if cursor.fetchone():

                return render_template(
                    "edit_student.html",
                    student=student,
                    error="Student number already exists."
                )

            if email:

                cursor.execute("""
                    SELECT student_id
                    FROM students
                    WHERE email = ?
                      AND student_id != ?
                """, (
                    email,
                    student_id
                ))

                if cursor.fetchone():

                    return render_template(
                        "edit_student.html",
                        student=student,
                        error="Email already exists."
                    )

            cursor.execute("""
                UPDATE students
                SET
                    student_number = ?,
                    first_name = ?,
                    last_name = ?,
                    email = ?,
                    course = ?,
                    year_level = ?
                WHERE student_id = ?
            """, (
                student_number,
                first_name,
                last_name,
                email if email else None,
                course if course else None,
                int(year_level) if year_level else None,
                student_id
            ))

            connection.commit()

            return redirect(url_for("students"))

        return render_template(
            "edit_student.html",
            student=student
        )

    finally:
        connection.close()


# =========================================================
# DELETE STUDENT
# =========================================================

@app.route(
    "/students/delete/<int:student_id>",
    methods=["POST"]
)
def delete_student(student_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT user_id
            FROM students
            WHERE student_id = ?
        """, (student_id,))

        student = cursor.fetchone()

        if student:

            user_id = student["user_id"]

            cursor.execute("""
                DELETE FROM students
                WHERE student_id = ?
            """, (student_id,))

            if user_id:

                cursor.execute("""
                    DELETE FROM users
                    WHERE user_id = ?
                """, (user_id,))

            connection.commit()

    finally:
        connection.close()

    return redirect(url_for("students"))

# =========================================================
# ACADEMIC RECORDS - LIST
# =========================================================

@app.route("/academic-records")
def academic_records():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] not in ("admin", "professor"):
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        base_query = """
            SELECT
                cl.class_id,
                c.course_code,
                c.course_title,
                cl.section,
                cl.school_year,
                cl.semester,
                p.first_name AS professor_first_name,
                p.last_name AS professor_last_name,
                COUNT(DISTINCT e.student_id) AS student_count
            FROM classes cl
            JOIN courses c ON cl.course_id = c.course_id
            JOIN professors p ON cl.professor_id = p.professor_id
            LEFT JOIN enrollments e ON cl.class_id = e.class_id
        """

        if session["role"] == "professor":
            base_query += " WHERE p.user_id = ? "

        base_query += """
            GROUP BY
                cl.class_id, c.course_code, c.course_title,
                cl.section, cl.school_year, cl.semester,
                p.first_name, p.last_name
            ORDER BY c.course_code, cl.section
        """

        if session["role"] == "professor":
            cursor.execute(base_query, (session["user_id"],))
        else:
            cursor.execute(base_query)

        classes_list = cursor.fetchall()

    finally:
        connection.close()

    return render_template("academic_records.html", classes=classes_list)


# =========================================================
# VIEW ACADEMIC RECORDS FOR A CLASS
# =========================================================

@app.route("/academic-records/class/<int:class_id>")
def view_class_records(class_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] not in ("admin", "professor"):
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        if not professor_owns_class(cursor, class_id):
            return "You are not authorized to view this class.", 403

        cursor.execute("""
            SELECT
                cl.class_id, cl.section, cl.school_year, cl.semester,
                c.course_code, c.course_title,
                p.first_name AS professor_first_name,
                p.last_name AS professor_last_name
            FROM classes cl
            JOIN courses c ON cl.course_id = c.course_id
            JOIN professors p ON cl.professor_id = p.professor_id
            WHERE cl.class_id = ?
        """, (class_id,))

        class_record = cursor.fetchone()

        if not class_record:
            return "Class not found.", 404

        cursor.execute("""
            SELECT
                e.enrollment_id, s.student_id, s.student_number,
                s.first_name, s.last_name, s.email,
                s.course, s.year_level
            FROM enrollments e
            JOIN students s ON e.student_id = s.student_id
            WHERE e.class_id = ?
            ORDER BY s.last_name, s.first_name
        """, (class_id,))

        students_list = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "class_records.html",
        class_record=class_record,
        students=students_list
    )


# =========================================================
# ENROLL STUDENT IN CLASS
# =========================================================

@app.route("/academic-records/class/<int:class_id>/enroll",
           methods=["GET", "POST"])
def enroll_student(class_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:

        cursor = connection.cursor()

        # -------------------------------------------------
        # Get class information
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                cl.class_id,
                cl.section,
                cl.school_year,
                cl.semester,
                c.course_code,
                c.course_title,
                p.first_name AS professor_first_name,
                p.last_name AS professor_last_name
            FROM classes cl
            JOIN courses c
                ON cl.course_id = c.course_id
            JOIN professors p
                ON cl.professor_id = p.professor_id
            WHERE cl.class_id = ?
        """, (class_id,))

        class_record = cursor.fetchone()

        if not class_record:
            return "Class not found.", 404

        # -------------------------------------------------
        # Get students NOT YET enrolled in this class
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                s.student_id,
                s.student_number,
                s.first_name,
                s.last_name,
                s.email,
                s.course,
                s.year_level
            FROM students s
            WHERE s.student_id NOT IN (
                SELECT student_id
                FROM enrollments
                WHERE class_id = ?
            )
            ORDER BY
                s.last_name,
                s.first_name
        """, (class_id,))

        available_students = cursor.fetchall()

        # -------------------------------------------------
        # Process enrollment
        # -------------------------------------------------

        if request.method == "POST":

            student_id = request.form.get(
                "student_id", ""
            ).strip()

            if not student_id:

                return render_template(
                    "enroll_student.html",
                    class_record=class_record,
                    students=available_students,
                    error="Please select a student."
                )

            # Check if student exists
            cursor.execute("""
                SELECT student_id
                FROM students
                WHERE student_id = ?
            """, (student_id,))

            student = cursor.fetchone()

            if not student:

                return render_template(
                    "enroll_student.html",
                    class_record=class_record,
                    students=available_students,
                    error="Student not found."
                )

            # Check duplicate enrollment
            cursor.execute("""
                SELECT enrollment_id
                FROM enrollments
                WHERE class_id = ?
                  AND student_id = ?
            """, (
                class_id,
                int(student_id)
            ))

            if cursor.fetchone():

                return render_template(
                    "enroll_student.html",
                    class_record=class_record,
                    students=available_students,
                    error="Student is already enrolled in this class."
                )

            # Create enrollment
            cursor.execute("""
                INSERT INTO enrollments
                (
                    class_id,
                    student_id
                )
                VALUES (?, ?)
            """, (
                class_id,
                int(student_id)
            ))

            connection.commit()

            return redirect(
                url_for(
                    "view_class_records",
                    class_id=class_id
                )
            )

        # -------------------------------------------------
        # Display enrollment form
        # -------------------------------------------------

        return render_template(
            "enroll_student.html",
            class_record=class_record,
            students=available_students
        )

    except Exception as e:

        connection.rollback()

        return render_template(
            "enroll_student.html",
            class_record=class_record,
            students=available_students,
            error=f"Unable to enroll student: {e}"
        )

    finally:

        connection.close()

# =========================================================
# ACADEMIC RECORD HELPERS
# =========================================================

def ensure_attendance_period_column(connection):
    """
    Adds period_id to attendance table if the existing database
    was created before grading-period support was added.
    """

    cursor = connection.cursor()

    cursor.execute("""
        PRAGMA table_info(attendance)
    """)

    columns = [row["name"] for row in cursor.fetchall()]

    if "period_id" not in columns:

        cursor.execute("""
            ALTER TABLE attendance
            ADD COLUMN period_id INTEGER
        """)

        connection.commit()


def professor_owns_class(cursor, class_id):

    if session.get("role") == "admin":
        return True

    cursor.execute("""
        SELECT 1
        FROM classes
        WHERE class_id = ?
        AND professor_id = (
            SELECT professor_id
            FROM professors
            WHERE user_id = ?
        )
    """, (
        class_id,
        session.get("user_id")
    ))

    return cursor.fetchone() is not None


def recompute_academic_factors(
    connection,
    enrollment_id,
    period_id
):

    cursor = connection.cursor()

    # =====================================================
    # ATTENDANCE
    # =====================================================

    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN status = 'Present'
                    THEN 1
                    ELSE 0
                END
            ) AS present
        FROM attendance
        WHERE enrollment_id = ?
        AND period_id = ?
    """, (
        enrollment_id,
        period_id
    ))

    attendance = cursor.fetchone()

    total_attendance = attendance["total"] or 0
    present_count = attendance["present"] or 0

    if total_attendance > 0:

        attendance_percentage = (
            present_count /
            total_attendance
        ) * 100

    else:

        attendance_percentage = 0


    # =====================================================
    # STUDY HOURS
    # =====================================================

    cursor.execute("""
        SELECT
            COALESCE(SUM(hours), 0) AS total_hours
        FROM study_hours
        WHERE enrollment_id = ?
        AND period_id = ?
    """, (
        enrollment_id,
        period_id
    ))

    study_hours = cursor.fetchone()["total_hours"] or 0


    # =====================================================
    # QUIZZES
    # =====================================================

    cursor.execute("""
        SELECT
            COALESCE(SUM(score), 0) AS earned,
            COALESCE(SUM(total_score), 0) AS possible
        FROM quizzes
        WHERE enrollment_id = ?
        AND period_id = ?
    """, (
        enrollment_id,
        period_id
    ))

    quiz = cursor.fetchone()

    if quiz["possible"] and quiz["possible"] > 0:

        quiz_average = (
            quiz["earned"] /
            quiz["possible"]
        ) * 100

    else:

        quiz_average = 0


    # =====================================================
    # ACTIVITIES
    # =====================================================

    cursor.execute("""
        SELECT
            COALESCE(SUM(score), 0) AS earned,
            COALESCE(SUM(total_score), 0) AS possible
        FROM activities
        WHERE enrollment_id = ?
        AND period_id = ?
    """, (
        enrollment_id,
        period_id
    ))

    activity = cursor.fetchone()

    if activity["possible"] and activity["possible"] > 0:

        activity_average = (
            activity["earned"] /
            activity["possible"]
        ) * 100

    else:

        activity_average = 0


    # =====================================================
    # EXAM
    # =====================================================

    cursor.execute("""
        SELECT
            score,
            total_score
        FROM exams
        WHERE enrollment_id = ?
        AND period_id = ?
        ORDER BY exam_id DESC
        LIMIT 1
    """, (
        enrollment_id,
        period_id
    ))

    exam = cursor.fetchone()

    if (
        exam
        and exam["score"] is not None
        and exam["total_score"] is not None
        and exam["total_score"] > 0
    ):

        exam_percentage = (
            exam["score"] /
            exam["total_score"]
        ) * 100

    else:

        exam_percentage = None


    # Keep percentages within 0-100.

    attendance_percentage = max(
        0,
        min(100, attendance_percentage)
    )

    quiz_average = max(
        0,
        min(100, quiz_average)
    )

    activity_average = max(
        0,
        min(100, activity_average)
    )


    # =====================================================
    # SAVE COMPUTED FACTORS
    # =====================================================

    cursor.execute("""
        INSERT INTO academic_factors
        (
            enrollment_id,
            period_id,
            attendance_percentage,
            study_hours,
            quiz_average,
            activity_average,
            exam_percentage,
            computed_at
        )

        VALUES
        (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            CURRENT_TIMESTAMP
        )

        ON CONFLICT(enrollment_id, period_id)

        DO UPDATE SET

            attendance_percentage =
                excluded.attendance_percentage,

            study_hours =
                excluded.study_hours,

            quiz_average =
                excluded.quiz_average,

            activity_average =
                excluded.activity_average,

            exam_percentage =
                excluded.exam_percentage,

            computed_at =
                CURRENT_TIMESTAMP
    """, (
        enrollment_id,
        period_id,
        attendance_percentage,
        study_hours,
        quiz_average,
        activity_average,
        exam_percentage
    ))



# =========================================================
# AUTOMATIC ML PREDICTION
# =========================================================
def generate_prediction(
    connection,
    enrollment_id,
    period_id
):
    cursor = connection.cursor()

    # -----------------------------------------------------
    # CHECK IF THERE ARE ANY ACADEMIC RECORDS
    # -----------------------------------------------------
    cursor.execute("""
        SELECT
            (
                SELECT COUNT(*)
                FROM attendance
                WHERE enrollment_id = ?
                AND period_id = ?
            )
            +
            (
                SELECT COUNT(*)
                FROM study_hours
                WHERE enrollment_id = ?
                AND period_id = ?
            )
            +
            (
                SELECT COUNT(*)
                FROM quizzes
                WHERE enrollment_id = ?
                AND period_id = ?
            )
            +
            (
                SELECT COUNT(*)
                FROM activities
                WHERE enrollment_id = ?
                AND period_id = ?
            )
            +
            (
                SELECT COUNT(*)
                FROM exams
                WHERE enrollment_id = ?
                AND period_id = ?
            )
            AS total_records
    """, (
        enrollment_id, period_id,
        enrollment_id, period_id,
        enrollment_id, period_id,
        enrollment_id, period_id,
        enrollment_id, period_id
    ))

    record_count = cursor.fetchone()["total_records"] or 0

    # If there are no records, remove any old prediction.
    if record_count == 0:
        cursor.execute("""
            DELETE FROM predictions
            WHERE enrollment_id = ?
            AND period_id = ?
        """, (
            enrollment_id,
            period_id
        ))
        return

    # -----------------------------------------------------
    # GET COMPUTED ACADEMIC FACTORS
    # -----------------------------------------------------
    cursor.execute("""
        SELECT
            attendance_percentage,
            study_hours,
            quiz_average,
            activity_average,
            exam_percentage
        FROM academic_factors
        WHERE enrollment_id = ?
        AND period_id = ?
    """, (
        enrollment_id,
        period_id
    ))

    factors = cursor.fetchone()

    if not factors:
        return

    attendance_percentage = float(
        factors["attendance_percentage"] or 0
    )
    study_hours = float(
        factors["study_hours"] or 0
    )
    quiz_average = float(
        factors["quiz_average"] or 0
    )
    activity_average = float(
        factors["activity_average"] or 0
    )

    exam_percentage = factors["exam_percentage"]

    if exam_percentage is not None:
        exam_percentage = float(exam_percentage)

    # -----------------------------------------------------
    # RUN RANDOM FOREST
    # -----------------------------------------------------
    result = analyze_student(
        attendance_percentage,
        study_hours,
        quiz_average,
        activity_average,
        exam_percentage
    )

    # Convert NumPy values to normal Python values.
    risk_level = str(result["risk_level"])
    description = str(result["description"])
    feedback = str(result["feedback"])

    # -----------------------------------------------------
    # PREDICTION LABEL
    # -----------------------------------------------------
    if risk_level == "Low":
        prediction_label = "Low Risk"
    elif risk_level == "Moderate":
        prediction_label = "Moderate Risk"
    else:
        prediction_label = "High Risk"

    # -----------------------------------------------------
    # DELETE OLD PREDICTION
    # -----------------------------------------------------
    # This allows the system to update the prediction whenever
    # the professor changes an academic record.
    cursor.execute("""
        DELETE FROM predictions
        WHERE enrollment_id = ?
        AND period_id = ?
    """, (
        enrollment_id,
        period_id
    ))

    # -----------------------------------------------------
    # SAVE NEW PREDICTION
    # -----------------------------------------------------
    cursor.execute("""
        INSERT INTO predictions
        (
            enrollment_id,
            period_id,
            risk_level,
            prediction_label,
            description,
            feedback,
            predicted_at
        )
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        enrollment_id,
        period_id,
        risk_level,
        prediction_label,
        description,
        feedback
    ))

    prediction_id = cursor.lastrowid

    # -----------------------------------------------------
    # SAVE WEAK AREAS
    # -----------------------------------------------------
    for area in result["weak_areas"]:

        area = str(area)

        if area == "Attendance":
            reason = (
                f"Attendance is only "
                f"{attendance_percentage:.2f}%."
            )

        elif area == "Study Hours":
            reason = (
                f"Total study hours are only "
                f"{study_hours:.2f} hours."
            )

        elif area == "Quiz Performance":
            reason = (
                f"Quiz performance is only "
                f"{quiz_average:.2f}%."
            )

        elif area == "Activity Performance":
            reason = (
                f"Activity performance is only "
                f"{activity_average:.2f}%."
            )

        elif area == "Exam Performance":
            if exam_percentage is not None:
                reason = (
                    f"Exam performance is only "
                    f"{exam_percentage:.2f}%."
                )
            else:
                reason = "No exam record is available."

        else:
            reason = "This area needs improvement."

        cursor.execute("""
            INSERT INTO weak_areas
            (
                prediction_id,
                area_name,
                reason
            )
            VALUES (?, ?, ?)
        """, (
            prediction_id,
            area,
            reason
        ))

# =========================================================
# PREDICTIONS PAGE
# =========================================================

@app.route("/predictions")
def predictions():

    if "user_id" not in session:
        return redirect(url_for("login"))

    role = session["role"]

    if role not in ("admin", "professor", "student"):
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:

        ensure_attendance_period_column(connection)
        cursor = connection.cursor()

        # -----------------------------------------------------
        # AUTO-SYNC PREDICTIONS
        # -----------------------------------------------------
        # This makes the Predictions page work even for academic
        # records that were entered before automatic prediction
        # was added.
        # -----------------------------------------------------
        if role == "admin":

            cursor.execute("""
                SELECT
                    e.enrollment_id,
                    gp.period_id
                FROM enrollments e
                CROSS JOIN grading_periods gp
                ORDER BY e.enrollment_id, gp.period_id
            """)

        elif role == "professor":

            cursor.execute("""
                SELECT
                    e.enrollment_id,
                    gp.period_id
                FROM enrollments e

                JOIN classes cl
                    ON e.class_id = cl.class_id

                JOIN grading_periods gp
                    ON 1 = 1

                JOIN professors prof
                    ON cl.professor_id = prof.professor_id

                WHERE prof.user_id = ?

                ORDER BY e.enrollment_id, gp.period_id
            """, (session["user_id"],))

        else:

            cursor.execute("""
                SELECT
                    e.enrollment_id,
                    gp.period_id
                FROM enrollments e

                JOIN students s
                    ON e.student_id = s.student_id

                JOIN grading_periods gp
                    ON 1 = 1

                WHERE s.user_id = ?

                ORDER BY e.enrollment_id, gp.period_id
            """, (session["user_id"],))

        prediction_targets = cursor.fetchall()

        for target in prediction_targets:

            enrollment_id = target["enrollment_id"]
            period_id = target["period_id"]

            recompute_academic_factors(
                connection,
                enrollment_id,
                period_id
            )

            generate_prediction(
                connection,
                enrollment_id,
                period_id
            )

        connection.commit()

        # -----------------------------------------------------
        # GET PREDICTIONS FOR THE LOGGED-IN USER
        # -----------------------------------------------------
        base_query = """
            SELECT
                p.prediction_id,
                p.enrollment_id,
                p.period_id,
                p.risk_level,
                p.prediction_label,
                p.description,
                p.feedback,
                p.predicted_at,

                gp.period_name,

                s.student_id,
                s.student_number,
                s.first_name AS student_first_name,
                s.last_name AS student_last_name,

                cl.class_id,
                cl.section,
                cl.school_year,
                cl.semester,

                c.course_code,
                c.course_title,

                prof.first_name AS professor_first_name,
                prof.last_name AS professor_last_name

            FROM predictions p

            JOIN enrollments e
                ON p.enrollment_id = e.enrollment_id

            JOIN students s
                ON e.student_id = s.student_id

            JOIN classes cl
                ON e.class_id = cl.class_id

            JOIN courses c
                ON cl.course_id = c.course_id

            JOIN professors prof
                ON cl.professor_id = prof.professor_id

            JOIN grading_periods gp
                ON p.period_id = gp.period_id
        """

        if role == "admin":

            cursor.execute(
                base_query + """
                ORDER BY p.predicted_at DESC, p.prediction_id DESC
                """
            )

        elif role == "professor":

            cursor.execute(
                base_query + """
                WHERE prof.user_id = ?
                ORDER BY p.predicted_at DESC, p.prediction_id DESC
                """,
                (session["user_id"],)
            )

        else:

            cursor.execute(
                base_query + """
                WHERE s.user_id = ?
                ORDER BY p.predicted_at DESC, p.prediction_id DESC
                """,
                (session["user_id"],)
            )

        prediction_rows = cursor.fetchall()

        # -----------------------------------------------------
        # GET WEAK AREAS FOR EACH PREDICTION
        # -----------------------------------------------------
        predictions_list = []

        for prediction in prediction_rows:

            cursor.execute("""
                SELECT
                    area_name,
                    reason
                FROM weak_areas
                WHERE prediction_id = ?
                ORDER BY weak_area_id
            """, (prediction["prediction_id"],))

            weak_areas = cursor.fetchall()

            predictions_list.append({
                "prediction": prediction,
                "weak_areas": weak_areas
            })

        # -----------------------------------------------------
        # RISK COUNTS
        # -----------------------------------------------------
        low_count = sum(
            1 for item in predictions_list
            if item["prediction"]["risk_level"] == "Low"
        )

        moderate_count = sum(
            1 for item in predictions_list
            if item["prediction"]["risk_level"] == "Moderate"
        )

        high_count = sum(
            1 for item in predictions_list
            if item["prediction"]["risk_level"] == "High"
        )

    finally:
        connection.close()

    return render_template(
        "predictions.html",
        predictions=predictions_list,
        low_count=low_count,
        moderate_count=moderate_count,
        high_count=high_count
    )


def render_manage_academic_record(
    class_id,
    student_id,
    period_id,
    error=None,
    success=None
):

    connection = get_db_connection()

    try:

        ensure_attendance_period_column(connection)

        cursor = connection.cursor()


        # =================================================
        # CHECK CLASS ACCESS
        # =================================================

        if not professor_owns_class(
            cursor,
            class_id
        ):

            return (
                "You are not authorized to manage this class.",
                403
            )


        # =================================================
        # STUDENT INFORMATION
        # =================================================

        cursor.execute("""
            SELECT

                e.enrollment_id,

                s.student_id,
                s.student_number,
                s.first_name,
                s.last_name,
                s.email,
                s.course,
                s.year_level,

                cl.class_id,
                cl.section,
                cl.school_year,
                cl.semester,

                c.course_code,
                c.course_title,

                p.first_name AS professor_first_name,
                p.last_name AS professor_last_name

            FROM enrollments e

            JOIN students s
                ON e.student_id = s.student_id

            JOIN classes cl
                ON e.class_id = cl.class_id

            JOIN courses c
                ON cl.course_id = c.course_id

            JOIN professors p
                ON cl.professor_id = p.professor_id

            WHERE e.class_id = ?
            AND e.student_id = ?
        """, (
            class_id,
            student_id
        ))

        record = cursor.fetchone()


        if not record:

            return (
                "Student is not enrolled in this class.",
                404
            )


        # =================================================
        # GRADING PERIOD
        # =================================================

        cursor.execute("""
            SELECT *
            FROM grading_periods
            WHERE period_id = ?
        """, (
            period_id,
        ))

        period = cursor.fetchone()


        if not period:

            return (
                "Grading period not found.",
                404
            )


        enrollment_id = record["enrollment_id"]


        # =================================================
        # ATTENDANCE
        # =================================================

        cursor.execute("""
            SELECT
                attendance_id,
                class_date,
                status

            FROM attendance

            WHERE enrollment_id = ?
            AND period_id = ?

            ORDER BY
                class_date DESC,
                attendance_id DESC
        """, (
            enrollment_id,
            period_id
        ))

        attendance_rows = cursor.fetchall()


        # =================================================
        # STUDY HOURS
        # =================================================

        cursor.execute("""
            SELECT
                study_id,
                study_date,
                hours

            FROM study_hours

            WHERE enrollment_id = ?
            AND period_id = ?

            ORDER BY
                study_date DESC,
                study_id DESC
        """, (
            enrollment_id,
            period_id
        ))

        study_rows = cursor.fetchall()


        # =================================================
        # QUIZZES
        # =================================================

        cursor.execute("""
            SELECT
                quiz_id,
                quiz_name,
                score,
                total_score,
                quiz_date

            FROM quizzes

            WHERE enrollment_id = ?
            AND period_id = ?

            ORDER BY
                quiz_date DESC,
                quiz_id DESC
        """, (
            enrollment_id,
            period_id
        ))

        quiz_rows = cursor.fetchall()


        # =================================================
        # ACTIVITIES
        # =================================================

        cursor.execute("""
            SELECT
                activity_id,
                activity_name,
                score,
                total_score,
                activity_date

            FROM activities

            WHERE enrollment_id = ?
            AND period_id = ?

            ORDER BY
                activity_date DESC,
                activity_id DESC
        """, (
            enrollment_id,
            period_id
        ))

        activity_rows = cursor.fetchall()


        # =================================================
        # EXAM
        # =================================================

        cursor.execute("""
            SELECT
                exam_id,
                score,
                total_score,
                exam_date

            FROM exams

            WHERE enrollment_id = ?
            AND period_id = ?

            ORDER BY exam_id DESC

            LIMIT 1
        """, (
            enrollment_id,
            period_id
        ))

        exam_rows = cursor.fetchall()


        # =================================================
        # COMPUTED FACTORS
        # =================================================

        recompute_academic_factors(
            connection,
            enrollment_id,
            period_id
        )

        connection.commit()


        cursor.execute("""
            SELECT *
            FROM academic_factors

            WHERE enrollment_id = ?
            AND period_id = ?
        """, (
            enrollment_id,
            period_id
        ))

        factors = cursor.fetchone()


        return render_template(

            "manage_academic_record.html",

            record=record,

            period=period,

            factors=factors,

            attendance_rows=attendance_rows,

            study_rows=study_rows,

            quiz_rows=quiz_rows,

            activity_rows=activity_rows,

            exam_rows=exam_rows,

            error=error,

            success=success
        )


    finally:

        connection.close()


# =========================================================
# STUDENT ACADEMIC RECORD
# =========================================================

@app.route(
    "/academic-records/class/<int:class_id>/student/<int:student_id>"
)
def student_academic_record(
    class_id,
    student_id
):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session["role"] not in (
        "admin",
        "professor"
    ):

        return redirect(
            url_for("dashboard")
        )


    connection = get_db_connection()

    try:

        ensure_attendance_period_column(
            connection
        )

        cursor = connection.cursor()


        if not professor_owns_class(
            cursor,
            class_id
        ):

            return (
                "You are not authorized to view this class.",
                403
            )


        cursor.execute("""
            SELECT

                e.enrollment_id,

                s.student_id,
                s.student_number,
                s.first_name,
                s.last_name,
                s.email,
                s.course,
                s.year_level,

                cl.class_id,
                cl.section,
                cl.school_year,
                cl.semester,

                c.course_code,
                c.course_title,

                p.first_name AS professor_first_name,
                p.last_name AS professor_last_name

            FROM enrollments e

            JOIN students s
                ON e.student_id = s.student_id

            JOIN classes cl
                ON e.class_id = cl.class_id

            JOIN courses c
                ON cl.course_id = c.course_id

            JOIN professors p
                ON cl.professor_id = p.professor_id

            WHERE e.class_id = ?
            AND e.student_id = ?
        """, (
            class_id,
            student_id
        ))

        record = cursor.fetchone()


        if not record:

            return (
                "Student is not enrolled in this class.",
                404
            )


        # =================================================
        # GRADING PERIODS + FACTORS
        # =================================================

        cursor.execute("""
            SELECT

                gp.period_id,
                gp.period_name,

                af.attendance_percentage,
                af.study_hours,
                af.quiz_average,
                af.activity_average,
                af.exam_percentage

            FROM grading_periods gp

            LEFT JOIN academic_factors af

                ON af.period_id = gp.period_id

                AND af.enrollment_id = ?

            ORDER BY gp.period_id
        """, (
            record["enrollment_id"],
        ))

        periods = cursor.fetchall()


    finally:

        connection.close()


    return render_template(

        "student_academic_record.html",

        record=record,

        periods=periods
    )


# =========================================================
# MANAGE STUDENT ACADEMIC RECORD
# =========================================================

@app.route(
    "/academic-records/class/<int:class_id>/student/<int:student_id>/period/<int:period_id>",
    methods=["GET", "POST"]
)
def manage_student_academic_record(
    class_id,
    student_id,
    period_id
):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session["role"] not in (
        "admin",
        "professor"
    ):

        return redirect(
            url_for("dashboard")
        )


    connection = get_db_connection()

    try:

        ensure_attendance_period_column(
            connection
        )

        cursor = connection.cursor()


        if not professor_owns_class(
            cursor,
            class_id
        ):

            return (
                "You are not authorized to manage this class.",
                403
            )


        # =================================================
        # GET ENROLLMENT
        # =================================================

        cursor.execute("""
            SELECT enrollment_id

            FROM enrollments

            WHERE class_id = ?
            AND student_id = ?
        """, (
            class_id,
            student_id
        ))

        enrollment = cursor.fetchone()


        if not enrollment:

            return (
                "Student is not enrolled in this class.",
                404
            )


        enrollment_id = enrollment[
            "enrollment_id"
        ]


        # =================================================
        # CHECK GRADING PERIOD
        # =================================================

        cursor.execute("""
            SELECT *

            FROM grading_periods

            WHERE period_id = ?
        """, (
            period_id,
        ))

        period = cursor.fetchone()


        if not period:

            return (
                "Grading period not found.",
                404
            )


        # =================================================
        # POST ACTIONS
        # =================================================

        if request.method == "POST":

            action = request.form.get(
                "action",
                ""
            ).strip()


            # =================================================
            # ADD ATTENDANCE
            # =================================================

            if action == "add_attendance":

                class_date = request.form.get(
                    "class_date",
                    ""
                ).strip()

                status = request.form.get(
                    "status",
                    ""
                ).strip()


                if (
                    not class_date
                    or status not in (
                        "Present",
                        "Absent"
                    )
                ):

                    return render_manage_academic_record(
                        class_id,
                        student_id,
                        period_id,
                        error="Please enter a valid class date and attendance status."
                    )


                cursor.execute("""
                    INSERT INTO attendance
                    (
                        enrollment_id,
                        period_id,
                        class_date,
                        status
                    )

                    VALUES (?, ?, ?, ?)
                """, (
                    enrollment_id,
                    period_id,
                    class_date,
                    status
                ))


            # =================================================
            # DELETE ATTENDANCE
            # =================================================

            elif action == "delete_attendance":

                attendance_id = request.form.get(
                    "attendance_id",
                    ""
                ).strip()


                cursor.execute("""
                    DELETE FROM attendance

                    WHERE attendance_id = ?
                    AND enrollment_id = ?
                    AND period_id = ?
                """, (
                    attendance_id,
                    enrollment_id,
                    period_id
                ))


            # =================================================
            # ADD STUDY HOURS
            # =================================================

            elif action == "add_study":

                study_date = request.form.get(
                    "study_date",
                    ""
                ).strip()

                hours_text = request.form.get(
                    "hours",
                    ""
                ).strip()


                try:

                    hours = float(
                        hours_text
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    hours = -1


                if (
                    not study_date
                    or hours < 0
                ):

                    return render_manage_academic_record(
                        class_id,
                        student_id,
                        period_id,
                        error="Please enter a valid study date and study hours."
                    )


                cursor.execute("""
                    INSERT INTO study_hours
                    (
                        enrollment_id,
                        period_id,
                        study_date,
                        hours
                    )

                    VALUES (?, ?, ?, ?)
                """, (
                    enrollment_id,
                    period_id,
                    study_date,
                    hours
                ))


            # =================================================
            # DELETE STUDY HOURS
            # =================================================

            elif action == "delete_study":

                study_id = request.form.get(
                    "study_id",
                    ""
                ).strip()


                cursor.execute("""
                    DELETE FROM study_hours

                    WHERE study_id = ?
                    AND enrollment_id = ?
                    AND period_id = ?
                """, (
                    study_id,
                    enrollment_id,
                    period_id
                ))


            # =================================================
            # ADD QUIZ
            # =================================================

            elif action == "add_quiz":

                quiz_name = request.form.get(
                    "quiz_name",
                    ""
                ).strip()

                score_text = request.form.get(
                    "score",
                    ""
                ).strip()

                total_text = request.form.get(
                    "total_score",
                    ""
                ).strip()

                quiz_date = request.form.get(
                    "quiz_date",
                    ""
                ).strip() or None


                try:

                    score = float(
                        score_text
                    )

                    total_score = float(
                        total_text
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    score = -1
                    total_score = 0


                if (
                    not quiz_name
                    or score < 0
                    or total_score <= 0
                    or score > total_score
                ):

                    return render_manage_academic_record(
                        class_id,
                        student_id,
                        period_id,
                        error="Invalid quiz score. Score cannot exceed total score."
                    )


                cursor.execute("""
                    INSERT INTO quizzes
                    (
                        enrollment_id,
                        period_id,
                        quiz_name,
                        score,
                        total_score,
                        quiz_date
                    )

                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    enrollment_id,
                    period_id,
                    quiz_name,
                    score,
                    total_score,
                    quiz_date
                ))


            # =================================================
            # DELETE QUIZ
            # =================================================

            elif action == "delete_quiz":

                quiz_id = request.form.get(
                    "quiz_id",
                    ""
                ).strip()


                cursor.execute("""
                    DELETE FROM quizzes

                    WHERE quiz_id = ?
                    AND enrollment_id = ?
                    AND period_id = ?
                """, (
                    quiz_id,
                    enrollment_id,
                    period_id
                ))


            # =================================================
            # ADD ACTIVITY
            # =================================================

            elif action == "add_activity":

                activity_name = request.form.get(
                    "activity_name",
                    ""
                ).strip()

                score_text = request.form.get(
                    "score",
                    ""
                ).strip()

                total_text = request.form.get(
                    "total_score",
                    ""
                ).strip()

                activity_date = request.form.get(
                    "activity_date",
                    ""
                ).strip() or None


                try:

                    score = float(
                        score_text
                    )

                    total_score = float(
                        total_text
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    score = -1
                    total_score = 0


                if (
                    not activity_name
                    or score < 0
                    or total_score <= 0
                    or score > total_score
                ):

                    return render_manage_academic_record(
                        class_id,
                        student_id,
                        period_id,
                        error="Invalid activity score. Score cannot exceed total score."
                    )


                cursor.execute("""
                    INSERT INTO activities
                    (
                        enrollment_id,
                        period_id,
                        activity_name,
                        score,
                        total_score,
                        activity_date
                    )

                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    enrollment_id,
                    period_id,
                    activity_name,
                    score,
                    total_score,
                    activity_date
                ))


            # =================================================
            # DELETE ACTIVITY
            # =================================================

            elif action == "delete_activity":

                activity_id = request.form.get(
                    "activity_id",
                    ""
                ).strip()


                cursor.execute("""
                    DELETE FROM activities

                    WHERE activity_id = ?
                    AND enrollment_id = ?
                    AND period_id = ?
                """, (
                    activity_id,
                    enrollment_id,
                    period_id
                ))


            # =================================================
            # SAVE EXAM
            # =================================================

            elif action == "save_exam":

                exam_score_text = request.form.get(
                    "exam_score",
                    ""
                ).strip()

                exam_total_text = request.form.get(
                    "exam_total_score",
                    ""
                ).strip()

                exam_date = request.form.get(
                    "exam_date",
                    ""
                ).strip() or None


                # Blank = exam not yet available.

                if (
                    not exam_score_text
                    and not exam_total_text
                ):

                    cursor.execute("""
                        DELETE FROM exams

                        WHERE enrollment_id = ?
                        AND period_id = ?
                    """, (
                        enrollment_id,
                        period_id
                    ))


                else:

                    try:

                        exam_score = float(
                            exam_score_text
                        )

                        exam_total_score = float(
                            exam_total_text
                        )

                    except (
                        TypeError,
                        ValueError
                    ):

                        exam_score = -1
                        exam_total_score = 0


                    if (
                        exam_score < 0
                        or exam_total_score <= 0
                        or exam_score > exam_total_score
                    ):

                        return render_manage_academic_record(
                            class_id,
                            student_id,
                            period_id,
                            error="Invalid exam score. Score cannot exceed total score."
                        )


                    # Only one exam per period.

                    cursor.execute("""
                        DELETE FROM exams

                        WHERE enrollment_id = ?
                        AND period_id = ?
                    """, (
                        enrollment_id,
                        period_id
                    ))


                    cursor.execute("""
                        INSERT INTO exams
                        (
                            enrollment_id,
                            period_id,
                            score,
                            total_score,
                            exam_date
                        )

                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        enrollment_id,
                        period_id,
                        exam_score,
                        exam_total_score,
                        exam_date
                    ))


            else:

                return render_manage_academic_record(
                    class_id,
                    student_id,
                    period_id,
                    error="Unknown academic record action."
                )


            # =================================================
            # AUTOMATIC COMPUTATION
            # =================================================

            recompute_academic_factors(
                connection,
                enrollment_id,
                period_id
            )

            # =================================================
            # AUTOMATIC ML PREDICTION
            # =================================================

            generate_prediction(
                connection,
                enrollment_id,
                period_id
            )

            connection.commit()


            # =================================================
            # BACK TO MANAGE PAGE
            # =================================================

            return redirect(
                url_for(
                    "manage_student_academic_record",

                    class_id=class_id,

                    student_id=student_id,

                    period_id=period_id
                )
            )


        # =================================================
        # GET
        # =================================================

        return render_manage_academic_record(
            class_id,
            student_id,
            period_id
        )


    except Exception as e:

        connection.rollback()

        return (
            f"Unable to manage academic record: {e}",
            500
        )


    finally:

        connection.close()

# =========================================================
# DELETE ENTIRE ACADEMIC RECORD FOR ONE GRADING PERIOD
# =========================================================

@app.route(
    "/academic-records/class/<int:class_id>/student/<int:student_id>/period/<int:period_id>/delete",
    methods=["POST"]
)
def delete_period_academic_record(class_id, student_id, period_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Admin only for now
    if session["role"] != "admin":
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        # -------------------------------------------------
        # Verify that the student is enrolled in the class
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                e.enrollment_id,
                s.first_name,
                s.last_name,
                gp.period_name
            FROM enrollments e

            JOIN students s
                ON e.student_id = s.student_id

            JOIN grading_periods gp
                ON gp.period_id = ?

            WHERE e.class_id = ?
              AND e.student_id = ?
        """, (
            period_id,
            class_id,
            student_id
        ))

        record = cursor.fetchone()

        if not record:
            return "Student or grading period not found.", 404

        enrollment_id = record["enrollment_id"]

        # -------------------------------------------------
        # DELETE PREDICTIONS FIRST
        # -------------------------------------------------
        # weak_areas will also be deleted automatically
        # because weak_areas.prediction_id uses ON DELETE CASCADE.
        cursor.execute("""
            DELETE FROM predictions
            WHERE enrollment_id = ?
              AND period_id = ?
        """, (
            enrollment_id,
            period_id
        ))

        # -------------------------------------------------
        # DELETE ATTENDANCE
        # -------------------------------------------------
        cursor.execute("""
            DELETE FROM attendance
            WHERE enrollment_id = ?
              AND period_id = ?
        """, (
            enrollment_id,
            period_id
        ))

        # -------------------------------------------------
        # DELETE STUDY HOURS
        # -------------------------------------------------
        cursor.execute("""
            DELETE FROM study_hours
            WHERE enrollment_id = ?
              AND period_id = ?
        """, (
            enrollment_id,
            period_id
        ))

        # -------------------------------------------------
        # DELETE QUIZZES
        # -------------------------------------------------
        cursor.execute("""
            DELETE FROM quizzes
            WHERE enrollment_id = ?
              AND period_id = ?
        """, (
            enrollment_id,
            period_id
        ))

        # -------------------------------------------------
        # DELETE ACTIVITIES
        # -------------------------------------------------
        cursor.execute("""
            DELETE FROM activities
            WHERE enrollment_id = ?
              AND period_id = ?
        """, (
            enrollment_id,
            period_id
        ))

        # -------------------------------------------------
        # DELETE EXAM
        # -------------------------------------------------
        cursor.execute("""
            DELETE FROM exams
            WHERE enrollment_id = ?
              AND period_id = ?
        """, (
            enrollment_id,
            period_id
        ))

        # -------------------------------------------------
        # DELETE COMPUTED ACADEMIC FACTORS
        # -------------------------------------------------
        cursor.execute("""
            DELETE FROM academic_factors
            WHERE enrollment_id = ?
              AND period_id = ?
        """, (
            enrollment_id,
            period_id
        ))

        connection.commit()

    except Exception as e:

        connection.rollback()

        return f"Unable to delete academic records: {e}", 500

    finally:
        connection.close()

    # Return to Student Academic Record
    return redirect(url_for(
        "student_academic_record",
        class_id=class_id,
        student_id=student_id
    ))

# ========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)