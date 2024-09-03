import json
import logging
import requests
import msal
from flask import Flask, render_template, jsonify, redirect, url_for, session, request
from authlib.integrations.flask_client import OAuth
import os
from concurrent.futures import ProcessPoolExecutor
import time
from dotenv import load_dotenv
from credential import get_parameters

app = Flask(__name__)

# write microsoft Oauth
app.secret_key = os.urandom(24)

load_dotenv()

# OAuthの設定
oauth = OAuth(app)
oauth.register(
    name='microsoft',
    client_id=get_parameters('MS_CLIENT_ID'),
    client_secret=get_parameters('MS_CLIENT_SECRET'),
    authorize_url=f"https://login.microsoftonline.com/{get_parameters('TENANT')}/oauth2/v2.0/authorize",
    authorize_params=None,
    access_token_url=f"https://login.microsoftonline.com/{get_parameters('TENANT')}/oauth2/v2.0/token",
    access_token_params=None,
    refresh_token_url=None,
    client_kwargs={'scope': 'User.Read'}
)


# Load configuration
config = {
    "client_id":get_parameters("MS_CLIENT_ID"),
    "authority": get_parameters("AUTHORITY"),
    "secret": get_parameters("MS_CLIENT_SECRET"),
    "scope": [get_parameters("SCOPE")],  
}

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

# トークンチェックデコレータ
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def fetch_each_events(user_id):
    calendar_endpoint = f"https://graph.microsoft.com/v1.0/users/{user_id}/calendar/events"
    calendar_data = requests.get(
        calendar_endpoint,
        headers={'Authorization': 'Bearer ' + result['access_token']}
    ).json()
    return calendar_data

@app.route('/')
def index():
    if "access_token" in result:
        return render_template('index.html')
    return redirect(url_for('login'))


@app.route('/login')
def login():
    #redirect_uri = url_for('authorized', _external=True, _scheme='https')
    redirect_uri = url_for('authorized', _external=True)
    return oauth.microsoft.authorize_redirect(redirect_uri)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/login/authorized')
def authorized():    
    if "access_token" in result:
        return redirect(url_for('/'))
    return redirect(url_for('not_aibos_user'))

@app.route('/not_aibos_user')
def not_aibos_user():
    return render_template('not_aibos_user.html')

@app.route('/ones_calendar')
def ones_calendar():
    if "access_token" in result:
        return render_template('ones_calendar.html')
    return redirect(url_for('login'))

@app.route('/get_accounts')
def get_accounts():
    if "access_token" in result:
        users_endpoint = "https://graph.microsoft.com/v1.0/users"
        users_data = requests.get(
            users_endpoint,
            headers={'Authorization': 'Bearer ' + result['access_token']},
        ).json()
        return jsonify(users_data['value'])
    else:
        return jsonify([]), 400
    
@app.route('/get_each_calendar/<user_id>')
def get_each_calendar(user_id):
    users_endpoint = "https://graph.microsoft.com/v1.0/users"
        
    all_calendar_data = []
    calendar_endpoint = f"https://graph.microsoft.com/v1.0/users/{user_id}/calendar/events"

    calendar_data = requests.get(
        calendar_endpoint,
        headers={'Authorization': 'Bearer ' + result['access_token']},
    ).json()

    for event in calendar_data.get('value', []):
        all_calendar_data.append({
            "title": event.get("subject"),
            "start": event.get("start", {}).get("dateTime"),
            "end": event.get("end", {}).get("dateTime"),
            "description": event.get("bodyPreview"),
            "location": event.get("location", {}).get("displayName"),
            "organizerEmail": event.get("organizer", {}).get("emailAddress", {}).get("name"),
            "isCancelled": event.get("isCancelled", False)  # Get the isCancelled flag
        })
    
    return jsonify(all_calendar_data)        

@app.route('/get_events')
def get_events():
    if "access_token" in result:
        users_endpoint = "https://graph.microsoft.com/v1.0/users"
        users_data = requests.get(
            users_endpoint,
            headers={'Authorization': 'Bearer ' + result['access_token']},
        ).json()

        print(users_data)
        
        all_calendar_data = []
        users_data = []
        if "value" in users_data:

            with ProcessPoolExecutor(max_workers=10) as executor:
                for user in users_data["value"]:
                    user_id = user["id"]
                    end = time.time()
                    task = executor.submit(fetch_each_events, user_id)
                    users_data.append(task)
            print("users_data")
            print(users_data)
            for data in users_data:     
                for event in data.get('value', []):
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

@app.route('/get_events_office')
def get_events_office():
    if "access_token" in result:
        users_endpoint = "https://graph.microsoft.com/v1.0/users"
        start_date = '2024-06-20T00:00:00Z'  # 取得開始日時
        end_date = '2024-06-30T23:59:59Z' 
        params = {
            'startDateTime': start_date,
            'endDateTime': end_date,
        }
        users_data = requests.get(
            users_endpoint,
            headers={'Authorization': 'Bearer ' + result['access_token']},
        ).json()
        
        all_calendar_data = []
        if "value" in users_data:
            for user in users_data["value"]:
                user_id = user["id"]
                calendar_endpoint = f"https://graph.microsoft.com/v1.0/users/{user_id}/calendar/events"
                calendar_data = requests.get(
                    calendar_endpoint,
                    headers={'Authorization': 'Bearer ' + result['access_token']},
                    params=params
                ).json()
                for event in calendar_data.get('value', []):
                    if event.get("location", {}).get("displayName").find("京都") == -1:
                        continue
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
    app.run(debug=True, host='0.0.0.0', port=5000)


