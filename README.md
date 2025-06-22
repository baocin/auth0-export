# Auth0 User Export Tool

This tool exports all Auth0 users, their organization associations, roles, and metadata to an Excel file.

## Setup

1. Install dependencies using UV:
```bash
uv sync
```

2. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

3. Configure your Auth0 credentials in `.env`:
   - `AUTH0_DOMAIN`: Your Auth0 tenant domain (e.g., your-tenant.auth0.com)
   - `AUTH0_CLIENT_ID`: Your Auth0 application Client ID
   - `AUTH0_CLIENT_SECRET`: Your Auth0 application Client Secret
   - `AUTH0_AUDIENCE`: (Optional) Defaults to https://your-domain/api/v2/
   - `AUTH0_RATE_LIMIT_PER_SEC`: (Optional) Rate limit per second. Defaults to 2 for free/trial tenants. Set to 15 for paid tenants.

## Auth0 Application Setup

To use this tool, you need to create a Machine-to-Machine application in Auth0:

1. Go to your Auth0 Dashboard > Applications
2. Create a new application of type "Machine to Machine"
3. Authorize it for the Auth0 Management API
4. Grant the following scopes:
   - `read:users`
   - `read:user_idp_tokens`
   - `read:organizations`
   - `read:organization_members`
   - `read:organization_member_roles`
   - `read:roles`

## Usage

Run the export script:
```bash
uv run python auth0_export.py
```

The script will:
- Connect to your Auth0 tenant using the Management API
- Fetch all users with their metadata
- For each user, fetch their organization memberships
- For each organization membership, fetch the user's roles
- Export all data to an Excel file with timestamp

## Output

The Excel file includes the following information:
- User details (ID, email, name, etc.)
- Authentication information (last login, login count, connection type)
- Email verification and blocked status
- Organization associations
- Global roles and organization-specific roles
- User metadata and app metadata
- Timestamps (created, updated, last login)

The output file is named: `auth0_users_export_YYYYMMDD_HHMMSS.xlsx`

## Rate Limiting and Reliability

The script includes built-in rate limiting and retry mechanisms to handle Auth0 API limits:

- **Automatic Rate Limiting**: Respects Auth0's rate limits (2 req/sec for free tenants, 15 req/sec for paid)
- **Exponential Backoff**: Automatically retries failed requests with exponential backoff and jitter
- **Rate Limit Detection**: Monitors API response headers for rate limit warnings
- **Configurable Limits**: Set `AUTH0_RATE_LIMIT_PER_SEC` in your `.env` file based on your subscription

The script will automatically handle:
- HTTP 429 (Too Many Requests) errors
- Network timeouts and transient failures
- API rate limit exhaustion

For large exports, the script may take longer due to rate limiting, but it will complete successfully without manual intervention.