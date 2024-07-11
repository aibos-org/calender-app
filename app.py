import json
import logging
import requests
import msal
from flask import Flask, render_template, jsonify, redirect, url_for, session, request
from authlib.integrations.flask_client import OAuth
import os
from functools import wraps
import jwt

app = Flask(__name__)


# write microsoft Oauth
app.secret_key = os.urandom(24)

# OAuthの設定
# OAuthの設定
oauth = OAuth(app)
oauth.register(
    name='microsoft',
    client_id=os.environ.get('MS_CLIENT_ID', 'can not get client id'),
    client_secret=os.environ.get('MS_CLIENT_SECRET', 'can not get client secret'),
    authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
    authorize_params=None,
    access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
    access_token_params=None,
    refresh_token_url=None,
    client_kwargs={'scope': 'User.Read'}
)

# end Oauth

# jwt
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')

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

# トークンチェックデコレータ
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print("===========")
        if 'user' not in session:
            return redirect(url_for('login'))
        try:
            data = jwt.decode(session['user'], app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return redirect(url_for('login'))
        print("===========")
        print(data)
        if authorization(data['mail']):
            return f(*args, **kwargs)
        else:
            return redirect(url_for('not_aibos_user'))

    return decorated_function


def authorization(mail):
    response = oauth.microsoft.get('https://graph.microsoft.com/v1.0/me')
    user_info = response.json()
    for account in user_info['value']:
        if account['mail'] == mail:
            return True
    return False

@app.route('/')
@login_required
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/login')
def login():
    redirect_uri = url_for('authorized', _external=True)
    return oauth.microsoft.authorize_redirect(redirect_uri)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/login/authorized')
def authorized():
    token = oauth.microsoft.authorize_access_token()
    response = oauth.microsoft.get('https://graph.microsoft.com/v1.0/me')
    user_info = response.json()
    
    # user_infoをjwtに変換
    jwted_user_info = jwt.encode(user_info, app.config['JWT_SECRET_KEY'], algorithm='HS256')

    session['user'] = jwted_user_info
    mail = user_info['mail']
    
    
    if "access_token" in result:
        users_endpoint = "https://graph.microsoft.com/v1.0/users"
        users_data = requests.get(
            users_endpoint,
            headers={'Authorization': 'Bearer ' + result['access_token']},
        ).json()
        for account in users_data['value']:
            if account['mail'] == mail:
                return redirect(url_for('ones_calendar'))

    return redirect(url_for('not_aibos_user'))

@app.route('/not_aibos_user')
def not_aibos_user():
    return render_template('not_aibos_user.html')

@app.route('/ones_calendar')
@login_required
def ones_calendar():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('ones_calendar.html')

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
        start_date = '2024-06-20T00:00:00Z'
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


