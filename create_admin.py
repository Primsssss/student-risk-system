from werkzeug.security import generate_password_hash
from database import get_db_connection, init_db


# Make sure database and tables exist
init_db()

username = "admin"
password = "admin123"
role = "admin"

# Hash the password
hashed_password = generate_password_hash(password)

connection = get_db_connection()
cursor = connection.cursor()

# Check if admin already exists
cursor.execute("""
    SELECT user_id
    FROM users
    WHERE username = ?
""", (username,))

existing_user = cursor.fetchone()

if existing_user:

    # Update existing admin account
    cursor.execute("""
        UPDATE users
        SET password = ?, role = ?
        WHERE username = ?
    """, (
        hashed_password,
        role,
        username
    ))

    print("Existing admin account updated successfully!")

else:

    # Create new admin account
    cursor.execute("""
        INSERT INTO users
        (username, password, role)
        VALUES (?, ?, ?)
    """, (
        username,
        hashed_password,
        role
    ))

    print("New admin account created successfully!")


connection.commit()
connection.close()

print("--------------------------------")
print("Username: admin")
print("Password: admin123")
print("Role: admin")
print("--------------------------------")