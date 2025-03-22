from flask import Flask, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from flask_session import Session  # Session management
import os

app = Flask(__name__)

# 🔹 Database Configuration (SQLite)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tasks.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your_secret_key"  # Change this to a strong key
app.config["SESSION_TYPE"] = "filesystem"  # Required for Flask session
Session(app)

db = SQLAlchemy(app)

# 🔹 OAuth Setup for Google Authentication
oauth = OAuth(app)
GOOGLE_CLIENT_ID = "159794780790-332amcvnrumt7a6dh8onrvc384vd57rn.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

google = oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    redirect_uri="http://127.0.0.1:5000/oauth2callback",
    client_kwargs={"scope": "openid email profile"},
)

# 🔹 Task Model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default="pending")

# ✅ Create Database Tables
with app.app_context():
    db.create_all()

# 🔹 Home Route
@app.route("/")
def home():
    return "✅ Task Manager API is running!"

# 🔹 Google OAuth Login
@app.route("/login")
def login():
    return google.authorize_redirect("http://127.0.0.1:5000/oauth2callback")

# 🔹 Google OAuth Callback
@app.route("/oauth2callback")
def auth_callback():
    token = google.authorize_access_token()
    user_info = google.get("https://www.googleapis.com/oauth2/v1/userinfo").json()  # ✅ Fixed user info retrieval
    
    session["user"] = user_info  # Store user session
    return jsonify(user_info)

# 🔹 Logout
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

# 🔹 Add Task
@app.route("/add_task", methods=["POST"])
def add_task():
    if "user" not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    data = request.get_json()
    if not data or "task" not in data:
        return jsonify({"error": "Task is required!"}), 400
    
    new_task = Task(task=data["task"])
    db.session.add(new_task)
    db.session.commit()

    return jsonify({
        "message": "Task added successfully!",
        "task": {
            "id": new_task.id,
            "task": new_task.task,
            "status": new_task.status
        }
    }), 201

# 🔹 Get All Tasks
@app.route("/tasks", methods=["GET"])
def get_tasks():
    if "user" not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    tasks = Task.query.all()
    return jsonify([
        {"id": task.id, "task": task.task, "status": task.status}
        for task in tasks
    ])

# 🔹 Get Task by ID
@app.route("/task/<int:task_id>", methods=["GET"])
def get_task(task_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify({"id": task.id, "task": task.task, "status": task.status})

# 🔹 Update Task
@app.route("/update_task/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json()
    if "task" in data:
        task.task = data["task"]
    if "status" in data:
        task.status = data["status"]

    db.session.commit()
    return jsonify({"message": "Task updated!", "task": {
        "id": task.id,
        "task": task.task,
        "status": task.status
    }})

# 🔹 Delete Task
@app.route("/delete_task/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted successfully!"})

# 🔹 Run Flask App
if __name__ == "__main__":
    app.run(debug=True)
