from flask import Flask, redirect, url_for, session, request, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from flask_cors import CORS, cross_origin

import os

app = Flask(__name__)
cors = CORS(app)
app.secret_key = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'

# Path to the client_secret.json file downloaded from the Google API Console
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Replace 'your_redirect_uri' with your application's redirect URI
REDIRECT_URI = 'http://127.0.0.1:5000/oauth2callback'


def get_flow():
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )


@app.route('/')
def index():
    return 'Welcome to the Google Drive Integration App. <a href="/login">Connect Google Drive</a>'


@app.route('/login')
def login():
    flow = get_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',  # This parameter tells Google that your application needs to access the user's data even when the user is not actively using your app
        include_granted_scopes='true'   # This parameter ensures that the application can use previously granted permissions along with new permissions without requiring the user to grant all permissions again.
    )
    session['state'] = state
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = get_flow()
    if request.args.get('state') != state:
        return 'State mismatch error', 400
    flow.fetch_token(authorization_response=request.url)

    if not session.get('credentials'):
        session['credentials'] = credentials_to_dict(flow.credentials)

    return redirect(url_for('drive'))


@app.route('/drive')
def drive():
    credentials = Credentials(**session['credentials']) #** syntax in Python is used for keyword argument unpacking
    drive_service = build('drive', 'v3', credentials=credentials)

    # List the 10 most recently modified files
    results = drive_service.files().list(
        pageSize=20, fields="nextPageToken, files(id, name, kind, mimeType)").execute()
    items = results.get('files', [])

    if not items:
        return 'No files found.'
    else:
        files = [{'id': item['id'], 'name': item['name'],'kind': item['kind'], 'mimeType': item['mimeType']  } for item in items]
        return jsonify(files)


def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }


if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(debug=True)
