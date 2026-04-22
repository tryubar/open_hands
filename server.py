"""
Gmail Daily Dashboard - Flask Backend
Fetches daily emails from Gmail and serves the web interface.
"""

import os
import base64
import email
import json
import requests
from datetime import datetime, timedelta, timezone
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, request, redirect, session, jsonify, render_template
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Gmail API configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), 'client_secret.json')

# Slack API configuration (via Zapier MCP)
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
ZAPIER_API_URL = 'https://mcp.zapier.com/api/v1/connect'

# Simple in-memory cache
email_cache = {}
slack_cache = {}
CACHE_TTL = 300  # 5 minutes


def get_flow():
    """Create OAuth flow with client secrets."""
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=request.base_url.rsplit('/', 1)[0] + '/auth/callback'
    )


def login_required(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        return f(*args, **kwargs)
    return decorated_function


def decode_email_body(payload):
    """Decode email body from Gmail API payload."""
    body = ''
    if 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                break
            elif part.get('mimeType') == 'text/html' and 'data' in part.get('body', {}):
                if not body:  # Prefer plain text
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
            elif 'parts' in part:
                body = decode_email_body(part) or body
    elif 'data' in payload.get('body', {}):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
    
    # Clean HTML if present
    if body.startswith('<') and not all(x.isalpha() or x.isspace() or x in '<>="/' for x in body[:100]):
        # Likely HTML, strip tags roughly
        import re
        body = re.sub(r'<[^>]+>', ' ', body)
        body = re.sub(r'\s+', ' ', body)
    
    return body.strip()[:2000]  # Limit body size


def get_user_info(creds):
    """Get user profile info."""
    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()
    return profile


def fetch_emails(creds, max_results=50):
    """Fetch emails from the past 24 hours."""
    service = build('gmail', 'v1', credentials=creds)
    
    # Calculate date 24 hours ago
    date_24h_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    after_date = date_24h_ago.strftime('%Y/%m/%d')
    
    # Query for emails after the date
    query = f'after:{after_date}'
    
    # Get message list
    messages = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results
    ).execute()
    
    emails = []
    message_list = messages.get('messages', [])
    
    if not message_list:
        return emails
    
    # Fetch details for each message
    for msg_meta in message_list[:max_results]:
        try:
            msg = service.users().messages().get(
                userId='me',
                id=msg_meta['id'],
                format='full'
            ).execute()
            
            headers = {h['name'].lower(): h['value'] for h in msg['payload'].get('headers', [])}
            
            # Parse date
            raw_date = headers.get('date', '')
            try:
                # Try multiple date formats
                parsed_date = email.utils.parsedate_to_datetime(raw_date)
            except:
                parsed_date = datetime.now(timezone.utc)
            
            # Get body snippet
            body = decode_email_body(msg['payload'])
            
            emails.append({
                'id': msg['id'],
                'from': headers.get('from', 'Unknown'),
                'subject': headers.get('subject', '(No Subject)'),
                'date': parsed_date.isoformat(),
                'snippet': body[:200] if body else '',
                'body': body,
                'is_unread': 'UNREAD' in msg.get('labelIds', [])
            })
        except Exception as e:
            print(f"Error fetching message: {e}")
            continue
    
    return emails


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/auth/login')
def auth_login():
    """Initiate Google OAuth flow."""
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return "Error: client_secret.json not found. Please download it from Google Cloud Console.", 500
    
    flow = get_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)


@app.route('/auth/callback')
def auth_callback():
    """Handle OAuth callback."""
    state = session.get('state')
    if not state:
        return "Error: No state found in session", 400
    
    flow = get_flow()
    flow.fetch_token(
        authorization_response=request.url,
        state=state
    )
    
    session['credentials'] = dict(flow.credentials)
    
    # Clear email cache on new login
    global email_cache
    email_cache = {}
    
    return redirect('/')


@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    """Clear session and logout."""
    session.clear()
    global email_cache
    email_cache = {}
    return jsonify({'success': True})


@app.route('/api/emails')
@login_required
def api_emails():
    """Fetch emails for the authenticated user."""
    global email_cache
    
    creds_data = session.get('credentials')
    if not creds_data:
        return jsonify({'error': 'Not authenticated'}), 401
    
    creds = Credentials.from_authorized_user_info(creds_data)
    
    # Check cache
    cache_key = 'emails'
    if cache_key in email_cache:
        cached_time, cached_emails = email_cache[cache_key]
        if (datetime.now(timezone.utc) - cached_time).total_seconds() < CACHE_TTL:
            return jsonify({'emails': cached_emails, 'cached': True})
    
    try:
        emails = fetch_emails(creds)
        email_cache[cache_key] = (datetime.now(timezone.utc), emails)
        return jsonify({'emails': emails, 'cached': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user')
@login_required
def api_user():
    """Get user profile info."""
    creds_data = session.get('credentials')
    if not creds_data:
        return jsonify({'error': 'Not authenticated'}), 401
    
    creds = Credentials.from_authorized_user_info(creds_data)
    if creds.expired:
        creds.refresh(Request())
        session['credentials'] = dict(creds)
    
    try:
        profile = get_user_info(creds)
        return jsonify({
            'email': profile.get('emailAddress', 'Unknown'),
            'messagesTotal': profile.get('messagesTotal', 0)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    has_secret = os.path.exists(CLIENT_SECRETS_FILE)
    return jsonify({
        'status': 'healthy',
        'configured': has_secret,
        'gmail_configured': has_secret,
        'slack_configured': bool(SLACK_BOT_TOKEN),
        'message': 'client_secret.json found' if has_secret else 'client_secret.json not found - configure Google OAuth first'
    })


def fetch_slack_messages():
    """Fetch Slack messages from the last 24 hours via Zapier MCP."""
    if not SLACK_BOT_TOKEN:
        return {'error': 'Slack bot token not configured. Set SLACK_BOT_TOKEN environment variable.'}
    
    try:
        messages = []
        
        # Zapier MCP requires Accept: text/event-stream for SSE responses
        headers = {
            'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream'
        }
        
        # First, list channels
        channels_response = requests.post(
            'https://mcp.zapier.com/api/v1/connect',
            headers=headers,
            json={'jsonrpc': '2.0', 'method': 'slack_list_channels', 'params': {}, 'id': 1},
            timeout=30,
            stream=True
        )
        
        if channels_response.status_code != 200:
            return {'error': f'Zapier MCP error: {channels_response.status_code}'}
        
        # Parse SSE response
        channels_data = []
        for line in channels_response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]  # Remove 'data: '
                    try:
                        data = json.loads(data_str)
                        if 'result' in data:
                            channels_data = data['result'].get('channels', [])
                    except:
                        pass
        
        date_24h_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        
        for channel in channels_data:
            channel_id = channel.get('id')
            channel_name = channel.get('name')
            
            if not channel_id:
                continue
            
            # Get channel history
            history_response = requests.post(
                'https://mcp.zapier.com/api/v1/connect',
                headers=headers,
                json={
                    'jsonrpc': '2.0',
                    'method': 'slack_conversations_history',
                    'params': {'channel': channel_id},
                    'id': 2
                },
                timeout=30,
                stream=True
            )
            
            if history_response.status_code == 200:
                # Parse SSE for history
                for line in history_response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                if 'result' in data:
                                    for msg in data['result'].get('messages', []):
                                        # Skip empty or system messages
                                        if not msg.get('text') or msg.get('subtype', '') in ['bot_message', 'channel_join', 'channel_leave']:
                                            continue
                                        
                                        # Convert timestamp
                                        ts = float(msg.get('ts', 0))
                                        msg_time = datetime.fromtimestamp(ts, tz=timezone.utc)
                                        
                                        if msg_time < date_24h_ago:
                                            continue
                                        
                                        messages.append({
                                            'channel': channel_name,
                                            'user': msg.get('user', 'Unknown'),
                                            'text': msg.get('text', ''),
                                            'timestamp': msg_time.isoformat(),
                                            'thread': bool(msg.get('thread_ts'))
                                        })
                            except:
                                pass
        
        messages.sort(key=lambda x: x['timestamp'], reverse=True)
        return messages
        
    except Exception as e:
        return {'error': str(e)}


@app.route('/api/slack/messages')
def api_slack_messages():
    """Fetch Slack messages for the authenticated user."""
    global slack_cache
    
    # Check cache
    cache_key = 'messages'
    if cache_key in slack_cache:
        cached_time, cached_messages = slack_cache[cache_key]
        if (datetime.now(timezone.utc) - cached_time).total_seconds() < CACHE_TTL:
            return jsonify({'messages': cached_messages, 'cached': True})
    
    result = fetch_slack_messages()
    
    if isinstance(result, dict) and 'error' in result:
        # Return demo messages if no Slack configured yet
        demo_messages = [
            {
                'channel': 'general',
                'user': 'Demo User',
                'text': 'Welcome to the Gmail + Slack Dashboard!',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'thread': False
            },
            {
                'channel': 'general',
                'user': 'Bot',
                'text': 'Connect your Slack workspace to see real messages',
                'timestamp': (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                'thread': False
            }
        ]
        return jsonify({
            'messages': demo_messages, 
            'cached': False,
            'demo': True,
            'note': result.get('error')
        })
    
    slack_cache[cache_key] = (datetime.now(timezone.utc), result)
    return jsonify({'messages': result, 'cached': False})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)