import json
import logging
import requests
import msal
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Load configuration
config = json.load(open("parameters.json"))

# Create a preferably long-lived app instance which maintains a token cache.
msal_app = msal.ConfidentialClientApplication(
    config["client_id"], authority=config["authority"],
    client_credential=config["secret"],
)

# The pattern to acquire a token looks like this.
result = None

# Firstly, looks up a token from cache
result = msal_app.acquire_token_silent(config["scope"], account=None)

if not result:
    logging.info("No suitable token exists in cache. Let's get a new one from AAD.")
    result = msal_app.acquire_token_for_client(scopes=config["scope"])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_events')
def get_events():
    if "access_token" in result:
        users_endpoint = "https://graph.microsoft.com/v1.0/users"
        users_data = requests.get(
            users_endpoint,
            headers={'Authorization': 'Bearer ' + result['access_token']}
        ).json()
        
        all_calendar_data = []
        if "value" in users_data:
            for user in users_data["value"]:
                user_id = user["id"]
                calendar_endpoint = f"https://graph.microsoft.com/v1.0/users/{user_id}/calendar/events"
                calendar_data = requests.get(
                    calendar_endpoint,
                    headers={'Authorization': 'Bearer ' + result['access_token']}
                ).json()
                for event in calendar_data.get('value', []):
                    all_calendar_data.append({
                        "organizer": user["displayName"],
                        "title": event.get("subject"),
                        "start": event.get("start", {}).get("dateTime"),
                        "end": event.get("end", {}).get("dateTime"),
                        "description": event.get("bodyPreview"),
                        "location": event.get("location", {}).get("displayName"),
                        "organizerEmail": event.get("organizer", {}).get("emailAddress", {}).get("name"),
                        "isCancelled": event.get("isCancelled", False)  # Get the isCancelled flag
                    })
        
        return jsonify(all_calendar_data)
    else:
        return jsonify([]), 400

if __name__ == '__main__':
    app.run(debug=True)
