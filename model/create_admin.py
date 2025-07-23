#python -m db.init_db --name "Admin User" --email admin@example.com --password admin123

import sqlite3
import os
from datetime import datetime
import bcrypt
import argparse

def create_admin(fullname, email, password):
    """Create an admin user with the given credentials if not already present."""
    db_path = os.path.join("db", "laila_central.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    created_at = datetime.utcnow().isoformat()

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone() is None:
        cursor.execute("""
            INSERT INTO users (
                fullname,
                email,
                password_hash,
                is_admin,
                created_at,
                is_confirmed,
                is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            fullname,
            email,
            hashed_password,
            1,  # is_admin
            created_at,
            1,  # is_confirmed
            1   # is_active
        ))
        print(f"✅ Admin user '{email}' created.")
    else:
        print(f"ℹ️ Admin user '{email}' already exists.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--name", required=True, help="Full name of the admin user")
    parser.add_argument("--email", required=True, help="Email address of the admin user")
    parser.add_argument("--password", required=True, help="Plaintext password for the admin user")

    args = parser.parse_args()
    create_admin(args.name, args.email, args.password)
