# Gmail Daily Emails Web App - Specification

## 1. Project Overview

**Project Name**: Gmail Daily Dashboard  
**Type**: Web Application (Flask + Vanilla JS)  
**Core Functionality**: Fetches daily emails from Gmail and messages from Slack, displaying them in a clean dashboard interface.  
**Target Users**: Individuals who want to quickly view their recent emails and Slack messages in a distraction-free web interface.

---

## 2. Functionality Specification

### 2.1 Core Features

- **Google OAuth2 Authentication**: Secure login flow using Google's OAuth 2.0 API
- **Email Fetching**: Retrieve emails from the past 24 hours using the Gmail API
- **Email Display**: Show sender, subject, date, and snippet for each email
- **Email Detail View**: Click to expand and view full email content
- **Logout**: Option to disconnect the Google account

### 2.2 User Interactions and Flows

1. **Landing Page**: User sees a "Sign in with Google" button
2. **OAuth Flow**: User authenticates with Google, granting read access to their Gmail
3. **Email Dashboard**: After auth, user sees list of today's emails
4. **Email Expansion**: User clicks an email to see full content
5. **Logout**: User can sign out to disconnect

### 2.3 Data Handling

- **Authentication Tokens**: Stored in session cookies (httpOnly)
- **Email Cache**: Brief in-memory cache to reduce API calls (5-minute TTL)
- **No Database**: Stateless design, no persistent storage

### 2.4 Edge Cases

- **No Emails**: Display friendly message "No emails today"
- **API Errors**: Show error message with retry button
- **Token Expiry**: Redirect to re-authentication
- **Rate Limiting**: Handle Gmail API quotas gracefully

---

## 3. UI/UX Specification

### 3.1 Layout Structure

```
┌─────────────────────────────────────────────────────┐
│  Header: Logo + User Info + Logout Button          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Main Content Area:                                  │
│  ┌─────────────────────────────────────────────┐   │
│  │  Email Card                                  │   │
│  │  - Sender avatar + name                     │   │
│  │  - Subject line                             │   │
│  │  - Date/time                               │   │
│  │  - Snippet (preview)                       │   │
│  │  [Expandable full content]                   │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  [More email cards...]                             │
│                                                     │
├─────────────────────────────────────────────────────┤
│  Footer: "Powered by Gmail API"                    │
└─────────────────────────────────────────────────────┘
```

### 3.2 Visual Design

**Color Palette**:
- Primary: `#1a73e8` (Google Blue)
- Secondary: `#f8f9fa` (Light Gray Background)
- Accent: `#34a853` (Success Green)
- Text Primary: `#202124` (Near Black)
- Text Secondary: `#5f6368` (Gray)
- Card Background: `#ffffff` (White)
- Border: `#dadce0` (Light Gray)
- Error: `#ea4335` (Red)

**Typography**:
- Font Family: `Inter` (Google Fonts) with fallback to system-ui
- Heading (H1): 24px, 600 weight
- Email Subject: 16px, 500 weight
- Body Text: 14px, 400 weight
- Timestamps: 12px, 400 weight

**Spacing System**:
- Base unit: 8px
- Card padding: 16px
- Card margin: 12px vertical
- Container max-width: 800px
- Border radius: 8px

**Visual Effects**:
- Card shadow: `0 1px 3px rgba(0,0,0,0.12)`
- Hover shadow: `0 2px 6px rgba(0,0,0,0.16)`
- Transition: all 0.2s ease

### 3.3 Components

**Sign-In Button**:
- Large rounded rectangle
- Google logo + "Sign in with Google"
- States: default (blue), hover (darker blue)

**Email Card**:
- White card with subtle shadow
- Avatar circle (32px, colored based on name initials)
- Hover: slight lift with enhanced shadow
- Expanded: shows full HTML body

**Header**:
- Sticky top
- User avatar (40px circle)
- Email address display
- Logout button (text style)

**Loading State**:
- Centered spinner animation
- "Loading your emails..." text

**Empty State**:
- Large envelope icon
- "No emails today" message
- Check back tomorrow note

---

## 4. Technical Specification

### 4.1 Backend (Flask)

**Endpoints**:
- `GET /` - Serve the main HTML page
- `GET /auth/login` - Initiate Google OAuth flow
- `GET /auth/callback` - Handle OAuth callback
- `POST /auth/logout` - Clear session
- `GET /api/emails` - Fetch emails (requires auth)
- `GET /static/<file>` - Serve static assets

**Dependencies**:
- Flask
- google-auth-oauthlib
- google-api-python-client

### 4.2 Frontend

- Single HTML page with embedded CSS and JavaScript
- Vanilla JavaScript (no framework)
- Fetch API for backend communication

### 4.3 Gmail API Scope

- `https://www.googleapis.com/auth/gmail.readonly`

---

## 5. Acceptance Criteria

1. ✅ User can sign in with Google account
2. ✅ User sees list of emails from the past 24 hours
3. ✅ Each email shows sender, subject, date, and snippet
4. ✅ User can click to expand email and see full content
5. ✅ User can sign out and return to login page
6. ✅ App handles errors gracefully (no emails, API errors)
7. ✅ Responsive design works on mobile and desktop
8. ✅ Clean, professional appearance matching spec colors