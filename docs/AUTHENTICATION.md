# Authentication Setup Guide

## Prerequisites

1. Python 3.8+ installed
2. Dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

## Database Initialization

Before using authentication, initialize the database:

```bash
python scripts/init_db.py
```

This creates the SQLite database (`niklaus.db`) with the following tables:
- `users` - User accounts
- `submissions` - Analysis history
- `analysis_cache` - Result caching
- `audit_log` - Activity logging

## Creating Admin Users

### Method 1: Using the script

```bash
python scripts/create_admin.py
```

Enter email and name when prompted.

### Method 2: Via OAuth (automatic)

Admins are automatically created when logging in via OAuth if their email is in the admin list.

## OAuth Configuration

### 1. Copy the example file

```bash
cp secrets.toml.example .streamlit/secrets.toml
```

### 2. Configure OAuth Providers

#### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
5. Application type: "Web application"
6. Add authorized redirect URI: `http://localhost:8501`
7. Copy Client ID and Client Secret to `.streamlit/secrets.toml`:

```toml
GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "your-client-secret"
GOOGLE_REDIRECT_URI = "http://localhost:8501"
```

#### GitHub OAuth

1. Go to GitHub Settings → Developer settings → OAuth Apps → New OAuth App
2. Application name: "Niklaus"
3. Homepage URL: `http://localhost:8501`
4. Authorization callback URL: `http://localhost:8501`
5. Copy Client ID and Client Secret to `.streamlit/secrets.toml`:

```toml
GITHUB_CLIENT_ID = "your-client-id"
GITHUB_CLIENT_SECRET = "your-client-secret"
GITHUB_REDIRECT_URI = "http://localhost:8501"
```

#### Microsoft OAuth

1. Go to [Azure Portal](https://portal.azure.com/)
2. Azure Active Directory → App registrations → New registration
3. Name: "Niklaus"
4. Redirect URI: Web `http://localhost:8501`
5. Copy Application (client) ID to `.streamlit/secrets.toml`
6. Create client secret and copy to `.streamlit/secrets.toml`:

```toml
MICROSOFT_CLIENT_ID = "your-client-id"
MICROSOFT_CLIENT_SECRET = "your-client-secret"
MICROSOFT_TENANT_ID = "common"  # or your tenant ID
MICROSOFT_REDIRECT_URI = "http://localhost:8501"
```

### 3. Set Admin Emails

Add admin email addresses to `.streamlit/secrets.toml`:

```toml
ADMIN_EMAILS = [
    "admin@example.com",
    "another-admin@example.com"
]
```

## Running the Application

```bash
streamlit run app.py
```

## Features

### For Users
- OAuth login (Google, GitHub, Microsoft)
- View submission history
- Private analysis results
- Profile management

### For Admins
- All user features, plus:
- View all submissions
- Manage users
- System statistics
- Audit logs

## Architecture

```
auth/
├── models.py          # SQLAlchemy models (User, Submission, etc.)
├── database.py        # Database manager and session handling
├── repository.py      # Data access layer (CRUD operations)
├── oauth.py          # OAuth handlers for providers
├── config.py         # OAuth configuration loader
├── session.py        # Streamlit session management
└── decorators.py     # Auth decorators (@require_auth, @require_admin)

ui/auth/
├── login.py          # Login page UI
├── dashboard.py      # User dashboard
├── history.py        # Submission history view
├── profile.py        # User profile management
└── admin.py          # Admin panel

scripts/
├── init_db.py        # Initialize database
└── create_admin.py   # Create admin user manually
```

## Database Schema

### Users Table
- id (Primary Key)
- email (Unique)
- name
- role (user/admin)
- oauth_provider
- oauth_id
- avatar_url
- is_active
- is_verified
- created_at
- updated_at
- last_login_at

### Submissions Table
- id (Primary Key)
- user_id (Foreign Key)
- total_files
- total_pairs_analyzed
- analysis_time
- status
- has_high_similarity
- results_summary (JSON)
- created_at

### Analysis Cache Table
- id (Primary Key)
- cache_key (Unique)
- result_data (JSON)
- created_at
- expires_at

### Audit Log Table
- id (Primary Key)
- user_id (Foreign Key)
- action
- entity_type
- entity_id
- details (JSON)
- ip_address
- created_at

## Security Notes

1. **Never commit `.streamlit/secrets.toml` to version control**
2. Add `.streamlit/secrets.toml` to `.gitignore`
3. Use environment variables in production
4. Enable HTTPS in production
5. Rotate OAuth secrets periodically
6. Review audit logs regularly

## Troubleshooting

### "Database locked" error
- Close other connections to the database
- Use SQLite only for development (PostgreSQL recommended for production)

### OAuth not working
- Verify redirect URIs match exactly
- Check if OAuth app is approved/published
- Ensure secrets are correctly set in `.streamlit/secrets.toml`

### Permission denied errors
- Check database file permissions
- Ensure directory is writable

## Production Deployment

For production:

1. Use PostgreSQL instead of SQLite:
   ```bash
   export DATABASE_URL="postgresql://user:pass@host:5432/niklaus"
   ```

2. Enable HTTPS and set secure redirect URIs

3. Use environment variables instead of secrets.toml

4. Configure proper CORS settings

5. Enable rate limiting

6. Set up backup strategy for database