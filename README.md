# 🚀 Auth0 Export Tool

A beautiful CLI tool to export Auth0 users, organizations, and roles to Excel/JSON with fancy progress bars and interactive setup.

## ⚡ **Quick Start - One Command**

```bash
# Run directly from GitHub (no installation required)
uvx --from git+https://github.com/baocin/auth0-export auth0-export
```
<img width="982" alt="Untitled 3" src="https://github.com/user-attachments/assets/212ff27e-7d00-4569-bbe4-e132ed37a00f" />

## 🏃‍♂️ **Alternative Quick Start (if you don't have uv installed)**

```bash
# Run with quickstart script (downloads and runs automatically)
curl -sSL https://raw.githubusercontent.com/baocin/auth0-export/main/quickstart.sh | bash
```

## 📦 **Installation Options**

### Option 1: Run with uvx (Recommended)
```bash
# Run directly without installation
uvx --from git+https://github.com/baocin/auth0-export auth0-export
```

### Option 2: Install and Run
```bash
# Install with uv
uv add auth0-export

# Or install with pip
pip install auth0-export

# Run the tool
auth0-export
```

### Option 3: Development Setup
```bash
# Clone the repository
git clone https://github.com/baocin/auth0-export.git
cd auth0-export

# Install dependencies with uv
uv sync

# Run the tool locally
uv run auth0-export

# Or run specific commands
uv run auth0-export --email "user@example.com"
uv run auth0-export --format json
```

## 🎯 Features

- **🎨 Beautiful CLI** with colors, progress bars, and interactive prompts
- **👤 Single User Queries** by Auth0 ID or email address
- **🎭 Role Management** - assign/remove global and organization roles
- **📋 Role Discovery** - list all available roles in your tenant
- **📊 Beautiful Table Display** for user information and organization data
- **📄 JSON Export** for full exports or individual users
- **⚡ Smart Rate Limiting** with exponential backoff and jitter
- **🔄 Auto-retry** for failed requests with intelligent backoff
- **📊 Progress Tracking** with ETA and real-time updates
- **🛠️ Interactive Setup** for Auth0 credentials
- **📈 Export Statistics** showing file size and processing time
- **🚀 One-command execution** with uvx

## 🖥️ CLI Usage

### Basic Commands
```bash
# Export all users to Excel (default)
auth0-export

# Export all users to JSON
auth0-export --format json

# Query specific user by Auth0 ID
auth0-export --user-id "auth0|606133e92be0f5006a51fd43"

# Query specific user by email
auth0-export --email "user@example.com"

# Display user info as pretty JSON in terminal
auth0-export --email "user@example.com" --json-pretty

# Export single user to JSON file
auth0-export --user-id "auth0|123..." --format json

# Custom output filename and rate limit
auth0-export -o users.xlsx -r 15

# Use custom .env file
auth0-export --env /path/to/my.env

# Setup credentials only
auth0-export --setup

# Quiet mode (minimal output)
auth0-export --quiet

# Show help
auth0-export --help
```

### Role Management Commands
```bash
# List all available roles in the tenant
auth0-export --list-roles

# Assign global role to user
auth0-export --email "user@example.com" --assign-global-role "rol_abcd1234"

# Assign organization role to user
auth0-export --user-id "auth0|123..." --assign-org-role "rol_efgh5678" --org-id "org_xyz9876"

# Remove global role from user
auth0-export --email "user@example.com" --remove-global-role "rol_abcd1234"

# Remove organization role from user
auth0-export --user-id "auth0|123..." --remove-org-role "rol_efgh5678" --org-id "org_xyz9876"

# Check user's roles after modification
auth0-export --email "user@example.com"
```

### Configuration

The tool will interactively prompt you for Auth0 credentials on first run, or you can create a `.env` file:

```bash
# Auth0 Management API Configuration
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your_client_id
AUTH0_CLIENT_SECRET=your_client_secret
AUTH0_AUDIENCE=https://your-tenant.auth0.com/api/v2/

# Rate Limiting Configuration (optional)
# Free/trial tenants: 2 requests/second (default)
# Paid tenants: 15 requests/second
AUTH0_RATE_LIMIT_PER_SEC=2
```

**Custom .env files:**
```bash
# Use different .env file for different tenants
auth0-export --env .env.production
auth0-export --env .env.staging --email "user@staging.com"
auth0-export --env /path/to/tenant-specific.env --format json
```

The tool will automatically show which .env file it's loading and the path it's looking for.

## 🔧 Auth0 Setup

To use this tool, you need to create a Machine-to-Machine application in Auth0:

1. Go to your Auth0 Dashboard > Applications
2. Create a new application of type "Machine to Machine"
3. Authorize it for the Auth0 Management API
4. Grant the following scopes:
   - `read:users` - for reading user profiles and metadata
   - `read:user_idp_tokens` - for reading user authentication tokens
   - `read:organizations` - for reading organization information
   - `read:organization_members` - for reading organization memberships
   - `read:organization_member_roles` - for reading organization-specific roles
   - `read:roles` - for reading available roles
   - `update:users` - for assigning/removing global roles (if using role management)
   - `update:organization_members` - for assigning/removing organization roles (if using role management)

The CLI will guide you through this setup process interactively.

## 📊 Export Data & Query Features

### Full Export (Excel/JSON)
Comprehensive data export includes:
- **User Information**: ID, email, name, profile details
- **Authentication**: Last login, login count, email verification status
- **Organizations**: All organization memberships (multiple rows per user if needed)
- **Roles**: Global roles and organization-specific roles
- **Metadata**: User metadata and app metadata fields
- **Timestamps**: Created, updated, and last login dates
- **Connections**: Authentication providers and connection types

### Single User Queries
Query individual users and display beautiful tables with:
- **User Profile**: Complete user information with verification status
- **Organization Memberships**: Table showing all organizations and roles
- **Global Roles**: Personal account roles and permissions
- **Export Options**: Save individual user data as JSON or Excel
- **Terminal Display**: Pretty-formatted tables or JSON output

### Role Management
Manage user roles directly from the CLI:
- **List Roles**: View all available roles in your Auth0 tenant with descriptions
- **Assign Global Roles**: Add roles to users for tenant-wide permissions
- **Assign Organization Roles**: Add roles to users within specific organizations
- **Remove Roles**: Remove global or organization-specific roles from users
- **Bulk Operations**: Combine role management with user queries for efficient workflows

### Export Formats
- **Excel (.xlsx)**: Structured spreadsheet with auto-adjusted columns
- **JSON (.json)**: Complete structured data with metadata
- **Terminal Display**: Rich formatted tables for single users

## 🚀 Rate Limiting & Reliability

The tool includes enterprise-grade reliability features:

- **Automatic Rate Limiting**: Respects Auth0's limits (2 req/sec free, 15 req/sec paid)
- **Exponential Backoff**: Intelligent retry with jitter to prevent thundering herd
- **Rate Limit Detection**: Monitors API headers for proactive throttling
- **Progress Tracking**: Real-time ETA and processing statistics
- **Configurable Limits**: Automatic detection of subscription type

For large exports (1000+ users), the tool may take time but will complete reliably:
- Free tenants: ~8-10 minutes per 1000 users
- Paid tenants: ~1-2 minutes per 1000 users

## 🎨 CLI Features

### Interactive Setup
- Beautiful welcome banner with ASCII art
- Step-by-step credential configuration
- Subscription type detection for optimal rate limits
- Automatic .env file creation

### Progress Tracking
- Real-time progress bars with spinners
- Current user being processed
- Estimated time remaining
- Processing statistics

### Export Summary
- File size and location
- Processing time and rate limits
- Option to open Excel file immediately
- Export statistics table

## 🛠️ Development

### Requirements
- Python 3.12+
- uv (recommended) or pip

### Dependencies
- `auth0-python`: Auth0 Management API client
- `pandas` + `openpyxl`: Excel export functionality
- `click`: CLI framework
- `rich`: Beautiful terminal output
- `blessings`: Terminal colors and formatting

### Building
```bash
# Install development dependencies
uv sync

# Build package
uv build

# Run tests (if available)
uv run pytest
```

## 📝 License

**Commercial License** - Free for individuals, $15/user/month for companies.

- **Individual Use**: Free for personal projects and individual use
- **Commercial Use**: $15 USD per user per month for companies and organizations
- **Contact**: auth0managementtool@steele.red for commercial licensing

See LICENSE file for complete terms and conditions.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🐛 Issues

Found a bug or have a feature request? Please open an issue on [GitHub](https://github.com/baocin/auth0-export/issues).

## 🎉 Credits

Built with ❤️ using:
- [Auth0 Python SDK](https://github.com/auth0/auth0-python)
- [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- [Blessings](https://github.com/erikrose/blessings) for terminal formatting
- [Click](https://click.palletsprojects.com/) for CLI framework
