import os
import json
import secrets
import logging
from flask import Flask, jsonify, redirect, request, session, url_for
from models import db, Email, CalendarEvent, Contact # Ensure this is correctly importing from models.py
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from flask_sqlalchemy import SQLAlchemy  # Ensure this is imported
from datetime import datetime
from flask_migrate import Migrate


# Allow OAuth to work on HTTP (Only for development)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['DEBUG'] = True



# Securely generate a secret key
app.secret_key = secrets.token_hex(16)  # Change this to a secure random key

# ✅ Configure the database URI properly
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'project_data.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Initialize the database
db.init_app(app)
# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Create tables if they don’t exist
with app.app_context():
    print("Creating database...")
    db.create_all()
    print("Database created successfully!")




# Google OAuth 2.0 Scopes
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

# Load Client Config
CLIENT_SECRETS_FILE = "credentials.json"


# -------------------- Google OAuth Authentication --------------------

@app.route("/login")
def login():
    flow = Flow.from_client_secrets_file(
        "credentials.json", 
        scopes = SCOPES,
        redirect_uri="http://127.0.0.1:5000/oauth2callback"
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    session["state"] = state
    return redirect(authorization_url)


@app.route("/oauth2callback")
def oauth2callback():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES,
        state=session["state"],
        redirect_uri=url_for("oauth2callback", _external=True)
    )

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

    # Save token.json for future use
    with open("token.json", "w") as token_file:
        json.dump(session["credentials"], token_file)

    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.pop("credentials", None)
    return redirect(url_for("home"))


def get_credentials():
    """Retrieve credentials from session or token.json."""
    creds = None
    if "credentials" in session:
        creds = Credentials(**session["credentials"])
    elif os.path.exists("token.json"):
        with open("token.json", "r") as token_file:
            creds_data = json.load(token_file)
            creds = Credentials(**creds_data)

    # Refresh the token if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"Token refresh error: {e}")
            return None

    return creds


# -------------------- Google API Integrations --------------------

@app.route("/")
def home():
    return "Google API Integration is working! Visit /login to authenticate."


@app.route("/calendar")
def get_calendar_events():
    creds = get_credentials()
    if not creds:
        return redirect(url_for("login"))

    service = build("calendar", "v3", credentials=creds)
    events_result = service.events().list(
        calendarId="primary", maxResults=10, singleEvents=True, orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])
    stored_events = []
    
    for event in events:
        title = event.get("summary", "No Title")
        description = event.get("description", "")
        start_time = event["start"].get("dateTime", event["start"].get("date"))
        end_time = event["end"].get("dateTime", event["end"].get("date"))

        # Convert time string to datetime
        start_time = datetime.fromisoformat(start_time)
        end_time = datetime.fromisoformat(end_time)

        # Check if event already exists (to avoid duplicates)
        existing_event = CalendarEvent.query.filter_by(title=title, start_time=start_time).first()
        if not existing_event:
            new_event = CalendarEvent(
                title=title, description=description, start_time=start_time, end_time=end_time
            )
            db.session.add(new_event)
        
        stored_events.append({
            "title": title, "description": description, "start_time": start_time, "end_time": end_time
        })

    db.session.commit()  # Save all events

    return jsonify(stored_events)


@app.route("/contacts")
def get_contacts():
    creds = get_credentials()
    if not creds:
        return redirect(url_for("login"))

    service = build("people", "v1", credentials=creds)
    results = service.people().connections().list(
        resourceName="people/me", personFields="names,emailAddresses"
    ).execute()

    contacts = results.get("connections", [])
    stored_contacts = []

    for person in contacts:
        name = person.get("names", [{}])[0].get("displayName", "Unknown")
        email = person.get("emailAddresses", [{}])[0].get("value", "")

        # Check if contact already exists (avoid duplicates)
        existing_contact = Contact.query.filter_by(email=email).first()
        if not existing_contact:
            new_contact = Contact(name=name, email=email)
            db.session.add(new_contact)

        stored_contacts.append({"name": name, "email": email})

    db.session.commit()  # Save all contacts

    return jsonify(stored_contacts)


@app.route("/emails", methods=["GET"])
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
        headers = {header["name"]: header["value"] for header in msg_detail["payload"]["headers"]}

        subject = headers.get("Subject", "No Subject")
        sender = headers.get("From", "Unknown Sender")
        snippet = msg_detail.get("snippet", "")
        date_received = datetime.now()  # Current timestamp

        # Check if email already exists (avoid duplicates)
        existing_email = Email.query.filter_by(subject=subject, sender=sender, snippet=snippet).first()
        if not existing_email:
            new_email = Email(sender=sender, subject=subject, snippet=snippet, date_received=date_received)
            db.session.add(new_email)

        # Append email data for API response
        email_data.append({
            "id": msg["id"],
            "subject": subject,
            "from": sender,
            "snippet": snippet
        })

    db.session.commit()  # Save all new emails in database

    return jsonify(email_data)

if __name__ == "__main__":
    app.run(debug=True)
