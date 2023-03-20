from flask import Flask, redirect, request, url_for, session, render_template
from google.oauth2 import credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
import sqlite3
import random
import requests
import re
from functools import wraps
from youtube import youtube

# Channel ID's of people that are allowed to approve unban requests
approved_users = [""]
config_file = "client_secrets.json"

yt_api = youtube(config_file)
with open(config_file, 'r') as f:
    oauth_config = json.load(f)['installed']

CLIENT_ID = oauth_config['client_id']
CLIENT_SECRET = oauth_config['client_secret']
REDIRECT_URI = oauth_config['redirect_uris'][0]

app = Flask(__name__)
app.secret_key = os.urandom(24)

def create_database():
    conn = sqlite3.connect('messages.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages (channel_id TEXT, banned_reason TEXT, unban_reason TEXT, video_link TEXT)''')
    conn.commit()
    conn.close()

def get_random_entry():
    conn = sqlite3.connect('messages.sqlite')
    c = conn.cursor()
    c.execute("SELECT * FROM messages")
    all_rows = c.fetchall()
    conn.close()
    return random.choice(all_rows) if all_rows else None

def delete_entry(channel_id):
    conn = sqlite3.connect('messages.sqlite')
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE channel_id=?", (channel_id,))
    conn.commit()
    conn.close()

def channel_id_exists(channel_id):
    conn = sqlite3.connect('messages.sqlite')
    c = conn.cursor()
    c.execute("SELECT EXISTS(SELECT 1 FROM messages WHERE channel_id=?)", (channel_id,))
    exists = c.fetchone()[0]
    conn.close()
    return bool(exists)

def save_message(channel_id, banned_reason, unban_reason, video_link):
    if channel_id_exists(channel_id):
        return False  # Return False if the Channel ID already exists in the database.

    conn = sqlite3.connect('messages.sqlite')
    c = conn.cursor()
    c.execute("INSERT INTO messages (channel_id, banned_reason, unban_reason, video_link) VALUES (?, ?, ?, ?)", (channel_id, banned_reason, unban_reason, video_link))
    conn.commit()
    conn.close()
    return True

create_database()

def check_channel_id(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return redirect('/')
        
        creds = credentials.Credentials.from_authorized_user_info(info=json.loads(session['credentials']))
        youtube = build('youtube', 'v3', credentials=creds)
        try:
            response = youtube.channels().list(part='id', mine=True).execute()
            channel_id = response['items'][0]['id']
        except HttpError:
            channel_id = None

        if channel_id not in approved_users:
            return "Access denied. You are not allowed to view this page."

        return f(*args, **kwargs)
    return decorated_function




@app.route('/')
def index():
    flow = Flow.from_client_config({
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "revoke_uri": "https://oauth2.googleapis.com/revoke",
            "redirect_uris": [REDIRECT_URI]
        }
    }, scopes=['https://www.googleapis.com/auth/youtube.readonly'])

    flow.redirect_uri = REDIRECT_URI
    authorization_url, _ = flow.authorization_url(prompt='consent')
    return redirect(authorization_url)


@app.route('/callback')
def callback():
    flow = Flow.from_client_config({
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "revoke_uri": "https://oauth2.googleapis.com/revoke",
            "redirect_uris": [REDIRECT_URI]
        }
    }, scopes=['https://www.googleapis.com/auth/youtube.readonly'])

    flow.redirect_uri = REDIRECT_URI
    flow.fetch_token(code=request.args.get('code'))

    session['credentials'] = credentials.Credentials.to_json(flow.credentials)
    return redirect(url_for('store_message'))


@app.route('/store_message', methods=['GET', 'POST'])
def store_message():
    if 'credentials' not in session:
        return redirect(url_for('index'))

    creds_info = json.loads(session['credentials'])
    creds = credentials.Credentials.from_authorized_user_info(info=creds_info)
    youtube = build('youtube', 'v3', credentials=creds)

    if request.method == 'POST':
        banned_reason = request.form['banned_reason']
        unban_reason = request.form['unban_reason']
        video_link = request.form['video_link']

        try:
            channels_response = youtube.channels().list(
                part='id',
                mine=True
            ).execute()

            channel_id = channels_response['items'][0]['id']

            # Store the details in the database
            success = save_message(channel_id, banned_reason, unban_reason, video_link)
            if success:
                return f"Message from Channel ID {channel_id} saved successfully."
            else:
                return f"Message from Channel ID {channel_id} not saved. Only one entry per Channel ID is allowed."
        except HttpError as e:
            return f"An error occurred: {e}"

    return render_template('message_form.html')




@app.route('/review_request', methods=['GET', 'POST'])
@check_channel_id
def review_request():
    entry = get_random_entry()
    if entry is None:
        return "No entries found in the database."

    channel_id, banned_reason, unban_reason, video_link = entry

    if request.method == 'POST':
        action = request.form['action']
        if action == 'accept':
            # Send POST request to your desired URL
            # Replace 'https://your-url-here.com' with your actual URL
            delete_entry(channel_id)
            return redirect(url_for('unban', channel_id=channel_id))
        elif action == 'reject':
            delete_entry(channel_id)
        elif action == 'skip':
            pass
        
        
        return redirect(url_for('review_request'))

    return render_template('review_request.html', channel_id=channel_id, banned_reason=banned_reason, unban_reason=unban_reason, video_link=video_link)

@app.route("/unban", methods=['GET'])
@check_channel_id
def unban():
    try:
        channel_id = request.args.get('channel_id')
        yt_api.unban(channel_id)
        return redirect(url_for('review_request'))
    except:
        return "Error"

def youtube_video_id(url):
    patterns = [
        r'(?:https?://)?(?:www\.)?youtu\.?be(?:\.com)?/(?:watch\?v=)?(?:embed/)?(\w+)(?:\?t=(\d+))?',
        r'(?:https?://)?(?:www\.)?youtu\.?be(?:\.com)?/watch\?(?:.+&)?v=(\w+)(?:&t=(\d+))?',
    ]

    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            return match.group(1), match.group(2)

    return None, None

app.jinja_env.filters['youtube_video_id'] = youtube_video_id

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
