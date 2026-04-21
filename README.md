# Gmail Daily Dashboard

A simple web app that fetches and displays your daily emails from Gmail.

## Setup Instructions

### 1. Create Google OAuth Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services** > **Library
4. Search for "Gmail API" and enable it
5. Go to **APIs & Services** > **Credentials**
6. Click **Create Credentials** > **OAuth client ID**
7. Set application type to **Web application**
8. Add authorized redirect URI: `http://localhost:5000/auth/callback`
9. Download the JSON file and rename it to `client_secret.json`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the App

```bash
python server.py
```

### 4. Access the App

Open your browser and go to: [http://localhost:5000](http://localhost:5000)

## Configuration

- Copy `client_secret.example.json` to `client_secret.json` and fill in your credentials
- For production, set a secure `SECRET_KEY` environment variable:
  ```bash
  export SECRET_KEY='your-secure-random-key'
  ```

## Features

- Google OAuth2 authentication
- View emails from the past 24 hours
- Expandable email content
- Responsive design
- 5-minute email cache

## Security Notes

- Keep `client_secret.json` private and never commit it
- Use HTTPS in production
- Set a strong `SECRET_KEY` in production