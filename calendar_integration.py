from flask import Flask, jsonify, redirect, request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os

app = Flask(__name__)

# OAuth 2.0 SCOPES for Calendar, Contacts, and Gmail
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/gmail.readonly"
]

# Authenticate and get credentials
def authenticate_google():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # Check if credentials exist and are valid
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError("Missing 'credentials.json'. Please add it and try again.")

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES, 
                redirect_uri="http://127.0.0.1:5000/oauth2callback"
            )
            creds = flow.run_local_server(port=5000)

        # Save the refreshed credentials
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds

# Fetch Google Calendar Events
def get_calendar_events():
    creds = authenticate_google()
    service = build("calendar", "v3", credentials=creds)
    
    events_result = service.events().list(
        calendarId="primary",
        maxResults=10,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    events = events_result.get("items", [])
    return events

# Fetch Google Contacts
def get_contacts():
    creds = authenticate_google()
    service = build("people", "v1", credentials=creds)
    
    results = service.people().connections().list(
        resourceName="people/me",
        personFields="names,emailAddresses"
    ).execute()
    
    contacts = results.get("connections", [])
    return contacts

# Fetch Emails from Gmail
def get_emails():
    creds = authenticate_google()
    service = build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(userId="me", maxResults=10).execute()
    messages = results.get("messages", [])

    email_data = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId="me", id=msg["id"], format="metadata").execute()
        headers = {header["name"]: header["value"] for header in msg_detail["payload"]["headers"]}

        email_data.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "No Subject"),
            "from": headers.get("From", "Unknown Sender"),
            "snippet": msg_detail.get("snippet", "")
        })

    return email_data

# Flask Routes
@app.route("/calendar", methods=["GET"])
def calendar():
    return jsonify(get_calendar_events())

@app.route("/contacts", methods=["GET"])
def contacts():
    return jsonify(get_contacts())

@app.route("/emails", methods=["GET"])
def emails():
    return jsonify(get_emails())

# Handle OAuth2 callback
@app.route("/oauth2callback")
def oauth2callback():
    return "OAuth2 authentication successful. You can close this window."

if __name__ == "__main__":
    app.run(debug=True)
