import sqlite3

# Connect to SQLite (or create the database if it doesn’t exist)
conn = sqlite3.connect("tasks.db")  # This creates a database file named tasks.db
cursor = conn.cursor()

# Create a table to store tasks (if not already created)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        due_date TEXT,
        completed INTEGER DEFAULT 0
    )
''')

# Commit changes and close connection
conn.commit()
conn.close()

print("Database and tasks table created successfully!")
