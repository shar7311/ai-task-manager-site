import os
import json
import secrets
import logging
from datetime import datetime, timedelta

from flask import Flask, jsonify, redirect, request, session, url_for
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from flask_migrate import Migrate

from extensions import db
from models import Email, CalendarEvent, Contact, DailyLog, Task
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ml_model import predict_priority

from calendar_to_task import process_all_events_to_tasks


# -------------------- App Config --------------------
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['DEBUG'] = True
app.secret_key = secrets.token_hex(16)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'project_data.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)
CORS(app)


# -------------------- Blueprints --------------------
from routes.reminder import reminder
from routes.notification import notification
app.register_blueprint(reminder)
app.register_blueprint(notification)

# -------------------- DB Setup --------------------
with app.app_context():
    db.create_all()
    print("✅ Database initialized.")


# -------------------- Google OAuth --------------------
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid"
]
CLIENT_SECRETS_FILE = "credentials.json"

@app.route("/")
def home():
    return "✅ Google API Integration is working! Visit /login to authenticate."


@app.route("/login")
def login():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=url_for("oauth2callback", _external=True))
    authorization_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
    session["state"] = state
    return redirect(authorization_url)


@app.route("/oauth2callback")
def oauth2callback():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES, state=session["state"], redirect_uri=url_for("oauth2callback", _external=True))
    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials
    session["credentials"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }

    with open("token.json", "w") as token_file:
        json.dump(session["credentials"], token_file)

    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.pop("credentials", None)
    return redirect(url_for("home"))


def get_credentials():
    creds = None
    if "credentials" in session:
        creds = Credentials(**session["credentials"])
    elif os.path.exists("token.json"):
        with open("token.json", "r") as token_file:
            creds = Credentials(**json.load(token_file))

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"⚠️ Token refresh error: {e}")
            return None

    return creds


# -------------------- Google API Routes --------------------
@app.route("/calendar")
def get_calendar_events():
    creds = get_credentials()
    if not creds:
        return redirect(url_for("login"))

    service = build("calendar", "v3", credentials=creds)
    events_result = service.events().list(calendarId="primary", maxResults=10, singleEvents=True, orderBy="startTime").execute()
    events = events_result.get("items", [])
    stored_events = []

    for event in events:
        title = event.get("summary", "No Title")
        description = event.get("description", "")
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))

        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)

        if not CalendarEvent.query.filter_by(title=title, start_time=start_dt).first():
            db.session.add(CalendarEvent(title=title, description=description, start_time=start_dt, end_time=end_dt))

        stored_events.append({"title": title, "description": description, "start_time": start_dt, "end_time": end_dt})

    db.session.commit()
    return jsonify(stored_events)


@app.route("/contacts")
def get_contacts():
    creds = get_credentials()
    if not creds:
        return redirect(url_for("login"))

    service = build("people", "v1", credentials=creds)
    results = service.people().connections().list(resourceName="people/me", personFields="names,emailAddresses").execute()
    contacts = results.get("connections", [])
    stored_contacts = []

    for person in contacts:
        name = person.get("names", [{}])[0].get("displayName", "Unknown")
        email = person.get("emailAddresses", [{}])[0].get("value", "")

        if not Contact.query.filter_by(email=email).first():
            db.session.add(Contact(name=name, email=email))

        stored_contacts.append({"name": name, "email": email})

    db.session.commit()
    return jsonify(stored_contacts)


@app.route("/emails")
def get_emails():
    creds = get_credentials()
    if not creds:
        return redirect(url_for("login"))

    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(userId="me", maxResults=10).execute()
    messages = results.get("messages", [])

    email_data = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId="me", id=msg["id"], format="metadata").execute()
        headers = {h["name"]: h["value"] for h in msg_detail["payload"]["headers"]}

        subject = headers.get("Subject", "No Subject")
        sender = headers.get("From", "Unknown")
        snippet = msg_detail.get("snippet", "")
        date_received = datetime.now()

        if not Email.query.filter_by(subject=subject, sender=sender, snippet=snippet).first():
            db.session.add(Email(sender=sender, subject=subject, snippet=snippet, date_received=date_received))

        email_data.append({"id": msg["id"], "subject": subject, "from": sender, "snippet": snippet})

    db.session.commit()
    return jsonify(email_data)


# -------------------- Daily Logs --------------------
@app.route("/add-daily-log", methods=["POST"])
def add_daily_log():
    data = request.get_json()
    content = data.get("content")
    if not content:
        return jsonify({"error": "No content provided"}), 400

    db.session.add(DailyLog(content=content))
    db.session.commit()
    return jsonify({"message": "Daily log added successfully"}), 201


# -------------------- Task Management --------------------
@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.json
    priority = predict_priority(data)
    deadline = datetime.strptime(data['deadline'], '%Y-%m-%dT%H:%M')
    new_task = Task(
        title=data['title'],
        description=data.get('description'),
        deadline=deadline,
        estimated_time=data.get('estimated_time'),
        importance_level=data.get('importance_level'),
        category=data.get('category'),
        priority=priority
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify({'message': 'Task created', 'priority': priority}), 201


@app.route("/tasks", methods=["GET"])
def get_tasks():
    tasks = Task.query.all()
    return jsonify([{
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "due_date": t.deadline.isoformat() if t.deadline else None,
        "priority": t.priority,
        "status": t.status
    } for t in tasks])


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.json
    task.title = data.get("title", task.title)
    task.description = data.get("description", task.description)
    if "due_date" in data:
        task.deadline = datetime.fromisoformat(data["due_date"])
    task.priority = data.get("priority", task.priority)
    task.status = data.get("status", task.status)
    db.session.commit()
    return jsonify({"message": "Task updated"})


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted"})


# -------------------- Task Reminders --------------------
def check_due_tasks():
    now = datetime.now()
    upcoming = now + timedelta(minutes=1)
    due_tasks = Task.query.filter(Task.deadline <= upcoming, Task.reminded == False).all()
    
    for task in due_tasks:
        print(f"⏰ Reminder: {task.title} is due at {task.deadline}")
        task.reminded = True
        db.session.commit()


# -------------------- Calendar-to-Task Conversion --------------------
@app.route('/convert-calendar-to-tasks')
def convert_calendar_tasks():
    process_all_events_to_tasks()
    return "Calendar events converted to tasks!"


# -------------------- Scheduler Start --------------------
from scheduler import scheduler
scheduler.add_job(func=check_due_tasks, trigger="interval", seconds=60)


# -------------------- Run App --------------------
if __name__ == "__main__":
    scheduler.start()
    app.run(debug=True)
# This is a test change to check Git status