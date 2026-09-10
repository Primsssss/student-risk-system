# =========================================================
# RANDOM FOREST MODEL
# STUDENT ACADEMIC RISK PREDICTION SYSTEM
# =========================================================

from sklearn.ensemble import RandomForestClassifier


# =========================================================
# TRAINING DATA
# =========================================================
#
# Features:
# 1. Attendance Percentage
# 2. Study Hours
# 3. Quiz Average
# 4. Activity Average
# 5. Exam Percentage
#
# Exam = -1 means the exam is not yet available.
#
# NOTE:
# This is a prototype training dataset.
# Replace this with real historical labeled student data
# when the actual dataset is available.
# =========================================================

X_train = [
    # Attendance, Study, Quiz, Activity, Exam

    # LOW RISK
    [95, 40, 92, 94, 90],
    [90, 35, 88, 90, 85],
    [92, 30, 85, 88, 87],
    [98, 45, 95, 96, 92],
    [88, 32, 86, 84, -1],
    [90, 35, 90, 88, -1],
    [95, 40, 94, 92, -1],

    # MODERATE RISK
    [80, 20, 75, 78, 72],
    [78, 18, 70, 75, 68],
    [82, 22, 76, 74, 70],
    [75, 15, 72, 70, 65],
    [80, 20, 78, 76, -1],
    [77, 18, 73, 72, -1],
    [82, 22, 75, 78, -1],

    # HIGH RISK
    [60, 8, 55, 58, 50],
    [55, 5, 48, 52, 45],
    [65, 10, 58, 55, 48],
    [50, 4, 45, 48, 40],
    [62, 7, 52, 50, -1],
    [58, 6, 50, 55, -1],
    [65, 9, 55, 52, -1],
]


y_train = [
    # LOW
    "Low",
    "Low",
    "Low",
    "Low",
    "Low",
    "Low",
    "Low",

    # MODERATE
    "Moderate",
    "Moderate",
    "Moderate",
    "Moderate",
    "Moderate",
    "Moderate",
    "Moderate",

    # HIGH
    "High",
    "High",
    "High",
    "High",
    "High",
    "High",
    "High",
]


# =========================================================
# CREATE RANDOM FOREST MODEL
# =========================================================

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    max_depth=6
)


# =========================================================
# TRAIN MODEL
# =========================================================

model.fit(X_train, y_train)


# =========================================================
# PREDICT RISK
# =========================================================

def predict_risk(
    attendance_percentage,
    study_hours,
    quiz_average,
    activity_average,
    exam_percentage=None
):
    """
    Predict the student's academic risk.

    Exam is optional.
    If exam is not available, -1 is used.
    """

    if exam_percentage is None:
        exam_percentage = -1

    features = [[
        float(attendance_percentage),
        float(study_hours),
        float(quiz_average),
        float(activity_average),
        float(exam_percentage)
    ]]

    prediction = model.predict(features)[0]

    # Probability/confidence
    probabilities = model.predict_proba(features)[0]

    classes = model.classes_

    confidence = max(probabilities) * 100

    probability_map = {
        classes[i]: round(probabilities[i] * 100, 2)
        for i in range(len(classes))
    }

    return {
        "risk_level": prediction,
        "confidence": round(confidence, 2),
        "probabilities": probability_map
    }


# =========================================================
# GENERATE DESCRIPTION
# =========================================================

def generate_prediction_description(
    risk_level,
    attendance_percentage,
    study_hours,
    quiz_average,
    activity_average,
    exam_percentage=None
):
    """
    Generates a human-readable explanation
    based on the student's current academic factors.
    """

    if risk_level == "Low":

        description = (
            "The student is classified as Low Risk because "
            "of consistent attendance, sufficient study hours, "
            "and good performance in quizzes and activities. "
            "Based on the current academic records, the student "
            "shows a low risk of failing if the current "
            "performance is maintained."
        )

        feedback = (
            "Good job! Your academic performance is good. "
            "Continue studying hard and maintain your "
            "current performance."
        )

    elif risk_level == "Moderate":

        description = (
            "The student is classified as Moderate Risk because "
            "some academic factors are satisfactory while other "
            "areas need improvement. The student may still pass, "
            "but improving the identified areas can help reduce "
            "the risk of failing."
        )

        feedback = (
            "Your academic performance needs some improvement. "
            "Focus on your identified weak areas and continue "
            "working on your academic performance."
        )

    else:

        description = (
            "The student is classified as High Risk / Predicted "
            "to Fail because of low academic performance in one "
            "or more important factors. These academic factors "
            "indicate that the student may have difficulty "
            "meeting the course requirements if the current "
            "performance continues."
        )

        feedback = (
            "Your academic performance needs significant "
            "improvement. Please focus on your identified "
            "weak areas and complete the recommended learning "
            "modules."
        )

    return {
        "description": description,
        "feedback": feedback
    }


# =========================================================
# IDENTIFY WEAK AREAS
# =========================================================

def identify_weak_areas(
    attendance_percentage,
    study_hours,
    quiz_average,
    activity_average,
    exam_percentage=None
):
    """
    Identifies academic factors that need improvement.
    """

    weak_areas = []

    # Attendance
    if attendance_percentage < 75:
        weak_areas.append("Attendance")

    # Study Hours
    if study_hours < 10:
        weak_areas.append("Study Hours")

    # Quiz Performance
    if quiz_average < 75:
        weak_areas.append("Quiz Performance")

    # Activity Performance
    if activity_average < 75:
        weak_areas.append("Activity Performance")

    # Exam is only checked when available
    if exam_percentage is not None:
        if exam_percentage < 75:
            weak_areas.append("Exam Performance")

    return weak_areas


# =========================================================
# COMPLETE PREDICTION FUNCTION
# =========================================================

def analyze_student(
    attendance_percentage,
    study_hours,
    quiz_average,
    activity_average,
    exam_percentage=None
):
    """
    Complete student risk analysis.

    Returns:
        risk level
        confidence
        description
        feedback
        weak areas
    """

    result = predict_risk(
        attendance_percentage,
        study_hours,
        quiz_average,
        activity_average,
        exam_percentage
    )

    risk_level = result["risk_level"]

    explanation = generate_prediction_description(
        risk_level,
        attendance_percentage,
        study_hours,
        quiz_average,
        activity_average,
        exam_percentage
    )

    weak_areas = identify_weak_areas(
        attendance_percentage,
        study_hours,
        quiz_average,
        activity_average,
        exam_percentage
    )

    return {
        "risk_level": risk_level,
        "confidence": result["confidence"],
        "probabilities": result["probabilities"],
        "description": explanation["description"],
        "feedback": explanation["feedback"],
        "weak_areas": weak_areas
    }