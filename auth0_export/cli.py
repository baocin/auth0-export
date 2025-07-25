#!/usr/bin/env python3
"""
Beautiful CLI for Auth0 Export tool using blessings and rich for enhanced UX.
"""

import os
import sys
import time
import platform
from pathlib import Path
from typing import Optional, List

import click
try:
    from blessings import Terminal
    term = Terminal()
except ImportError:
    # Fallback for Windows where curses is not available
    class MockTerminal:
        def __getattr__(self, name):
            return ""
    term = MockTerminal()
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.json import JSON

try:
    from .exporter import Auth0Exporter
except ImportError:
    # Fallback for PyInstaller builds
    from auth0_export.exporter import Auth0Exporter

# Initialize console with Windows-safe settings
console = Console(
    force_terminal=True,
    width=120,
    legacy_windows=platform.system() == "Windows"
)

def safe_emoji(emoji: str, fallback: str = "") -> str:
    """Return emoji on non-Windows systems, fallback text on Windows."""
    return fallback if platform.system() == "Windows" else emoji

def print_banner():
    """Print a beautiful banner using rich."""
    rocket = safe_emoji("🚀 ", "")
    banner_panel = Panel(
        f"[bold white]{rocket}Auth0 Export Tool[/bold white]\n\n"
        "Export Auth0 users, organizations, and roles to Excel/JSON",
        title="",
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(banner_panel)

def check_credentials(env_file_path: Optional[str] = None) -> dict:
    """Check and get Auth0 credentials, prompting if needed."""
    # Determine .env file path
    search_icon = safe_emoji("🔍 ", "")
    if env_file_path:
        env_file = Path(env_file_path)
        console.print(f"{search_icon}Looking for credentials in: {env_file.absolute()}")
    else:
        env_file = Path('.env')
        console.print(f"{search_icon}Looking for credentials in: {env_file.absolute()}")
    
    # Load .env file
    from dotenv import load_dotenv
    checkmark = safe_emoji("✅ ", "")
    if env_file_path and env_file.exists():
        load_dotenv(env_file_path)
        console.print(f"{checkmark}Loaded credentials from: {env_file_path}")
    elif env_file.exists():
        load_dotenv(env_file)
        console.print(f"{checkmark}Loaded credentials from: {env_file.absolute()}")
    elif env_file_path:
        x_mark = safe_emoji("❌ ", "")
        console.print(f"{x_mark}[red]Custom .env file not found: {env_file.absolute()}[/red]")
        sys.exit(1)
    
    credentials = {
        'domain': os.getenv('AUTH0_DOMAIN'),
        'client_id': os.getenv('AUTH0_CLIENT_ID'),
        'client_secret': os.getenv('AUTH0_CLIENT_SECRET'),
        'audience': os.getenv('AUTH0_AUDIENCE'),
        'rate_limit': os.getenv('AUTH0_RATE_LIMIT_PER_SEC', '2')
    }
    
    # Check if .env exists
    if not env_file.exists() and not env_file_path:
        console.print(f"\n⚠️  [yellow]No .env file found at: {env_file.absolute()}[/yellow]")
        
        if Confirm.ask("Would you like to create one with your credentials?"):
            setup_credentials()
            return check_credentials()
        else:
            console.print("❌ [red]Credentials required. Exiting.[/red]")
            sys.exit(1)
    
    # Check if credentials are complete and not placeholder values
    missing = []
    placeholder_patterns = ['your-tenant', 'your_client', 'example.com', 'your-domain']
    
    for key, value in credentials.items():
        if key == 'audience':  # Skip audience as it's optional
            continue
        if not value or any(pattern in str(value) for pattern in placeholder_patterns):
            missing.append(key)
    
    if missing:
        console.print(f"\n⚠️  [yellow]Missing or placeholder credentials: {', '.join(missing)}[/yellow]")
        console.print("Please update your .env file with actual Auth0 credentials.")
        console.print(f"📁 Current .env path: {env_file.absolute()}")
        
        # Show current values (masked for security)
        console.print("\n📝 [dim]Current values:[/dim]")
        for key, value in credentials.items():
            if key == 'audience':
                continue
            if key == 'client_secret' and value and not any(pattern in str(value) for pattern in placeholder_patterns):
                console.print(f"   {key}: {'*' * 20}")  # Mask real secrets
            else:
                console.print(f"   {key}: {value or '[not set]'}")
        
        # If using custom env file, don't offer to create default .env
        if env_file_path:
            console.print("💡 Please add the actual credentials to your custom .env file.")
            sys.exit(1)
        
        if Confirm.ask("Would you like to update your .env file now?"):
            setup_credentials()
            return check_credentials()
        else:
            sys.exit(1)
    
    return credentials

def read_users_from_file(file_path: str, preview: bool = True) -> List[str]:
    """Read user emails/IDs from a file (one per line)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            users = [line.strip() for line in f if line.strip()]
        
        console.print(f"📁 Loaded {len(users)} users from {file_path}")
        
        if preview and users:
            # Show preview of users
            console.print("\n👥 [bold cyan]Users to process:[/bold cyan]")
            preview_count = min(10, len(users))
            for i, user in enumerate(users[:preview_count]):
                console.print(f"   {i+1:2d}. {user}")
            
            if len(users) > preview_count:
                console.print(f"   ... and {len(users) - preview_count} more users")
        
        return users
    except FileNotFoundError:
        console.print(f"❌ [red]File not found: {file_path}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ [red]Error reading file {file_path}: {e}[/red]")
        sys.exit(1)

def setup_credentials():
    """Interactive setup of Auth0 credentials."""
    console.print("\n🔧 [bold green]Setting up Auth0 credentials[/bold green]")
    
    # Display help text
    help_panel = Panel(
        "[bold]You'll need to create a Machine-to-Machine application in Auth0:[/bold]\n\n"
        "1. Go to Auth0 Dashboard > Applications\n"
        "2. Create new 'Machine to Machine' application\n"
        "3. Authorize for Auth0 Management API\n"
        "4. Grant scopes: read:users, read:organizations, read:organization_members, read:organization_member_roles, read:roles\n\n"
        "[dim]Press Enter to continue...[/dim]",
        title="📚 Setup Guide",
        border_style="blue"
    )
    console.print(help_panel)
    input()
    
    # Collect credentials
    domain = Prompt.ask("🌐 Auth0 Domain (e.g., your-tenant.auth0.com)")
    client_id = Prompt.ask("🔑 Client ID")
    client_secret = Prompt.ask("🔐 Client Secret", password=True)
    
    # Determine subscription type for rate limiting
    subscription_panel = Panel(
        "[bold]Rate Limiting Configuration:[/bold]\n\n"
        "• Free/Trial tenants: 2 requests/second\n"
        "• Paid tenants: 15 requests/second\n\n"
        "This affects export speed for large user bases.",
        title="⚡ Subscription Type",
        border_style="yellow"
    )
    console.print(subscription_panel)
    
    is_paid = Confirm.ask("Do you have a paid Auth0 subscription?", default=False)
    rate_limit = "15" if is_paid else "2"
    
    # Create .env file
    env_content = f"""# Auth0 Management API Configuration
AUTH0_DOMAIN={domain}
AUTH0_CLIENT_ID={client_id}
AUTH0_CLIENT_SECRET={client_secret}
AUTH0_AUDIENCE=https://{domain}/api/v2/

# Rate Limiting Configuration
AUTH0_RATE_LIMIT_PER_SEC={rate_limit}
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    console.print("\n✅ [bold green]Credentials saved to .env file[/bold green]")

def display_stats(exporter: Auth0Exporter, output_file: str):
    """Display export statistics in a beautiful table."""
    # Get file size
    file_size = os.path.getsize(output_file)
    file_size_mb = file_size / (1024 * 1024)
    
    # Create stats table
    table = Table(title="📊 Export Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    
    table.add_row("📁 Output File", output_file)
    table.add_row("📏 File Size", f"{file_size_mb:.2f} MB")
    table.add_row("⚡ Rate Limit", f"{exporter.rate_limit_per_second} req/sec")
    
    console.print(table)

def display_user_table(user_data: dict):
    """Display user information in a beautiful table format."""
    user = user_data['user']
    global_roles = user_data['global_roles']
    organizations = user_data['organizations']
    metadata = user_data['metadata']
    
    # User Information Table
    user_table = Table(title="👤 User Information", show_header=True, header_style="bold cyan")
    user_table.add_column("Field", style="cyan", no_wrap=True)
    user_table.add_column("Value", style="white")
    
    user_table.add_row("🆔 User ID", user.get('user_id', 'N/A'))
    user_table.add_row("📧 Email", user.get('email', 'N/A'))
    user_table.add_row("👤 Name", user.get('name', 'N/A'))
    user_table.add_row("🏷️ Nickname", user.get('nickname', 'N/A'))
    user_table.add_row("✅ Email Verified", str(user.get('email_verified', False)))
    user_table.add_row("🚫 Blocked", str(user.get('blocked', False)))
    user_table.add_row("📅 Created", user.get('created_at', 'N/A'))
    user_table.add_row("🔄 Updated", user.get('updated_at', 'N/A'))
    user_table.add_row("🕐 Last Login", user.get('last_login', 'N/A'))
    user_table.add_row("🔢 Login Count", str(user.get('logins_count', 0)))
    
    # Connection info
    identities = user.get('identities', [])
    if identities:
        connection = identities[0].get('connection', 'N/A')
        provider = identities[0].get('provider', 'N/A')
        user_table.add_row("🔗 Connection", connection)
        user_table.add_row("🌐 Provider", provider)
    
    console.print(user_table)
    
    # Global Roles Table
    if global_roles:
        roles_table = Table(title="🎭 Global Roles", show_header=True, header_style="bold yellow")
        roles_table.add_column("Role Name", style="yellow")
        roles_table.add_column("Role ID", style="dim")
        
        for role in global_roles:
            roles_table.add_row(
                role.get('name', 'N/A'),
                role.get('id', 'N/A')
            )
        console.print(roles_table)
    else:
        console.print("\n🎭 [bold yellow]Global Roles:[/bold yellow] [dim]None[/dim]")
    
    # Organizations Table
    if organizations:
        orgs_table = Table(title="🏢 Organization Memberships", show_header=True, header_style="bold green")
        orgs_table.add_column("Organization", style="green")
        orgs_table.add_column("Organization ID", style="dim")
        orgs_table.add_column("Display Name", style="bright_green")
        orgs_table.add_column("Roles", style="cyan")
        orgs_table.add_column("Metadata", style="dim")
        
        for org_data in organizations:
            org = org_data['organization']
            roles = org_data['roles']
            
            role_names = ', '.join([r.get('name', 'N/A') for r in roles]) if roles else 'None'
            metadata_str = str(org.get('metadata', {})) if org.get('metadata') else 'None'
            
            orgs_table.add_row(
                org.get('name', 'N/A'),
                org.get('id', 'N/A'),
                org.get('display_name', 'N/A'),
                role_names,
                metadata_str[:50] + '...' if len(metadata_str) > 50 else metadata_str
            )
        
        console.print(orgs_table)
    else:
        building_icon = safe_emoji("🏢 ", "")
        console.print(f"\n{building_icon}[bold green]Organizations:[/bold green] [dim]None[/dim]")
    
    # Summary
    chart_icon = safe_emoji("📈 ", "")
    summary_table = Table(title=f"{chart_icon}Summary", show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="magenta")
    summary_table.add_column("Count", style="white")
    
    building_icon = safe_emoji("🏢 ", "")
    masks_icon = safe_emoji("🎭 ", "")
    target_icon = safe_emoji("🎯 ", "")
    calendar_icon = safe_emoji("📅 ", "")
    
    summary_table.add_row(f"{building_icon}Organizations", str(metadata['total_organizations']))
    summary_table.add_row(f"{masks_icon}Global Roles", str(metadata['total_global_roles']))
    summary_table.add_row(f"{target_icon}Org Roles", str(metadata['total_org_roles']))
    summary_table.add_row(f"{calendar_icon}Export Time", metadata['export_timestamp'])
    
    console.print(summary_table)

@click.command()
@click.option('--output', '-o', help='Output filename (optional)')
@click.option('--rate-limit', '-r', type=int, help='Requests per second (overrides env var)')
@click.option('--setup', is_flag=True, help='Setup credentials interactively')
@click.option('--quiet', '-q', is_flag=True, help='Suppress progress output')
@click.option('--user-id', help='Query specific user by Auth0 ID (e.g., auth0|123...)')
@click.option('--email', help='Query specific user by email address')
@click.option('--format', type=click.Choice(['excel', 'json']), default='excel', help='Export format (excel or json)')
@click.option('--json-pretty', is_flag=True, help='Display JSON output in terminal (for single user)')
@click.option('--env', help='Path to custom .env file (default: .env in current directory)')
@click.option('--assign-global-role', help='Assign global role ID to user (requires --user-id or --email)')
@click.option('--assign-org-role', help='Assign organization role ID to user (requires --user-id or --email and --org-id)')
@click.option('--remove-global-role', help='Remove global role ID from user (requires --user-id or --email)')
@click.option('--remove-org-role', help='Remove organization role ID from user (requires --user-id or --email and --org-id)')
@click.option('--assign-to-org', is_flag=True, help='Assign user to organization (requires --user-id or --email and --org-id)')
@click.option('--remove-from-org', is_flag=True, help='Remove user from organization (requires --user-id or --email and --org-id)')
@click.option('--users-file', help='File containing list of user emails/IDs (one per line) for bulk operations')
@click.option('--org-id', help='Organization ID for role and organization operations')
@click.option('--list-roles', is_flag=True, help='List all available roles in the tenant')
@click.option('--list-orgs', is_flag=True, help='List all available organizations in the tenant')
@click.option('--debug-org-roles', help='Debug org roles for specific user ID and org ID (format: user_id,org_id)')
@click.option('--debug-api-methods', is_flag=True, help='Show available API methods for debugging')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompts for bulk operations')
@click.version_option(version="0.1.0", prog_name="auth0-export")
def main(output: Optional[str], rate_limit: Optional[int], setup: bool, quiet: bool, 
         user_id: Optional[str], email: Optional[str], format: str, json_pretty: bool, env: Optional[str],
         assign_global_role: Optional[str], assign_org_role: Optional[str], 
         remove_global_role: Optional[str], remove_org_role: Optional[str],
         assign_to_org: bool, remove_from_org: bool, users_file: Optional[str],
         org_id: Optional[str], list_roles: bool, list_orgs: bool, debug_org_roles: Optional[str], debug_api_methods: bool, yes: bool):
    """
    Export Auth0 users, organizations, and roles to Excel/JSON.
    
    This tool exports all users from your Auth0 tenant including:
    • User profiles and metadata
    • Organization memberships  
    • Global and organization-specific roles
    • Authentication history
    
    Examples:
      auth0-export                              # Export all users to Excel
      auth0-export --format json                # Export all users to JSON
      auth0-export --user-id auth0|123...       # Query specific user by ID
      auth0-export --email user@example.com     # Query specific user by email
      auth0-export --email user@example.com --json-pretty   # Display user in terminal
      auth0-export -o users.xlsx --rate-limit 15            # Custom filename and rate
      auth0-export --env /path/to/my.env        # Use custom .env file
      auth0-export --list-roles                 # List all available roles
      auth0-export --list-orgs                  # List all available organizations
      auth0-export --email user@example.com --assign-global-role rol_123   # Assign global role
      auth0-export --email user@example.com --assign-org-role rol_456 --org-id org_789  # Assign org role
      auth0-export --email user@example.com --assign-to-org --org-id org_123  # Assign user to organization
      auth0-export --users-file users.txt --assign-to-org --org-id org_123     # Bulk assign users to org
    """
    
    if not quiet:
        print_banner()
    
    # Handle setup mode
    if setup:
        setup_credentials()
        if not Confirm.ask("Continue with export?", default=True):
            return
    
    # Validate mutually exclusive options
    if user_id and email:
        console.print("❌ [red]Cannot specify both --user-id and --email. Choose one.[/red]")
        sys.exit(1)
    
    # Validate role management options
    role_actions = [assign_global_role, assign_org_role, remove_global_role, remove_org_role]
    org_actions = [assign_to_org, remove_from_org]
    
    if any(role_actions) and not (user_id or email or users_file):
        console.print("❌ [red]Role management requires --user-id, --email, or --users-file to specify the target user(s).[/red]")
        sys.exit(1)
    
    if any(org_actions) and not (user_id or email or users_file):
        console.print("❌ [red]Organization management requires --user-id, --email, or --users-file to specify the target user(s).[/red]")
        sys.exit(1)
    
    if (assign_org_role or remove_org_role or assign_to_org or remove_from_org) and not org_id:
        console.print("❌ [red]Organization operations require --org-id.[/red]")
        sys.exit(1)
    
    # Validate bulk operations
    if users_file and (user_id or email):
        console.print("❌ [red]Cannot specify both --users-file and individual user options (--user-id or --email).[/red]")
        sys.exit(1)
    
    # Check credentials
    credentials = check_credentials(env)
    
    if not quiet:
        console.print("\n🔍 [bold green]Connecting to Auth0...[/bold green]")
    
    try:
        # Initialize exporter
        exporter = Auth0Exporter()
        
        # Override rate limit if provided
        if rate_limit:
            exporter.rate_limit_per_second = rate_limit
            exporter.min_time_between_requests = 1.0 / rate_limit
            if not quiet:
                console.print(f"⚡ Rate limit set to {rate_limit} req/sec")
        
        # Handle list roles command
        if list_roles:
            if not quiet:
                console.print("\n📋 [bold yellow]Fetching available roles...[/bold yellow]")
            
            roles = exporter.get_available_roles()
            if roles:
                roles_table = Table(title="🎭 Available Roles", show_header=True, header_style="bold yellow")
                roles_table.add_column("Role Name", style="yellow")
                roles_table.add_column("Role ID", style="dim")
                roles_table.add_column("Description", style="white")
                
                for role in roles:
                    roles_table.add_row(
                        role.get('name', 'N/A'),
                        role.get('id', 'N/A'),
                        role.get('description', 'No description')[:60] + ('...' if len(role.get('description', '')) > 60 else '')
                    )
                
                console.print(roles_table)
                console.print(f"\n✅ Found {len(roles)} roles total")
            else:
                console.print("❌ [red]No roles found or unable to fetch roles.[/red]")
            return
        
        # Handle list organizations command
        if list_orgs:
            if not quiet:
                console.print("\n🏢 [bold green]Fetching available organizations...[/bold green]")
            
            orgs = exporter.get_available_organizations()
            if orgs:
                orgs_table = Table(title="🏢 Available Organizations", show_header=True, header_style="bold green")
                orgs_table.add_column("Organization Name", style="green")
                orgs_table.add_column("Organization ID", style="dim")
                orgs_table.add_column("Display Name", style="bright_green")
                orgs_table.add_column("Metadata", style="white")
                
                for org in orgs:
                    metadata_str = str(org.get('metadata', {})) if org.get('metadata') else 'None'
                    orgs_table.add_row(
                        org.get('name', 'N/A'),
                        org.get('id', 'N/A'),
                        org.get('display_name', 'N/A'),
                        metadata_str[:40] + ('...' if len(metadata_str) > 40 else metadata_str)
                    )
                
                console.print(orgs_table)
                console.print(f"\n✅ Found {len(orgs)} organizations total")
            else:
                console.print("❌ [red]No organizations found or unable to fetch organizations.[/red]")
            return
        
        # Handle debug API methods command
        if debug_api_methods:
            console.print("\n🔧 [bold blue]Available Auth0 API Methods:[/bold blue]")
            
            # Organizations methods
            org_methods = [m for m in dir(exporter.auth0.organizations) if not m.startswith('_')]
            console.print(f"\n📋 [bold yellow]Organizations methods ({len(org_methods)}):[/bold yellow]")
            for method in sorted(org_methods):
                console.print(f"   • {method}")
            
            # Role-related methods specifically
            role_methods = [m for m in org_methods if 'role' in m.lower()]
            console.print(f"\n🎭 [bold magenta]Role-related methods ({len(role_methods)}):[/bold magenta]")
            for method in sorted(role_methods):
                console.print(f"   • {method}")
            
            return
        
        # Handle debug org roles command
        if debug_org_roles:
            try:
                parts = debug_org_roles.split(',')
                if len(parts) != 2:
                    console.print("❌ [red]Debug format should be: user_id,org_id[/red]")
                    sys.exit(1)
                
                debug_user_id, debug_org_id = parts[0].strip(), parts[1].strip()
                console.print(f"\n🔍 [bold yellow]Debugging org roles for user {debug_user_id} in org {debug_org_id}[/bold yellow]")
                
                roles = exporter.get_user_organization_roles(debug_user_id, debug_org_id)
                console.print(f"\n📊 [bold]Results:[/bold] Found {len(roles)} roles")
                
                if roles:
                    roles_table = Table(title="🎭 Organization Roles Debug", show_header=True, header_style="bold yellow")
                    roles_table.add_column("Role Name", style="yellow")
                    roles_table.add_column("Role ID", style="dim")
                    roles_table.add_column("Description", style="white")
                    
                    for role in roles:
                        roles_table.add_row(
                            role.get('name', 'N/A'),
                            role.get('id', 'N/A'),
                            role.get('description', 'No description')[:60] + ('...' if len(role.get('description', '')) > 60 else '')
                        )
                    
                    console.print(roles_table)
                    
                    # Show raw data
                    console.print(f"\n📄 [bold]Raw API Response:[/bold]")
                    from rich.json import JSON
                    json_display = JSON.from_data(roles)
                    console.print(json_display)
                else:
                    console.print("❌ [red]No roles found or API call failed.[/red]")
                
            except Exception as e:
                console.print(f"❌ [red]Debug failed: {e}[/red]")
            return
        
        # Handle organization management actions
        org_actions = [assign_to_org, remove_from_org]
        role_actions = [assign_global_role, assign_org_role, remove_global_role, remove_org_role]
        
        if any(org_actions) or any(role_actions):
            # Get target users (single or bulk)
            target_users = []
            
            if users_file:
                # Bulk operation from file
                user_identifiers = read_users_from_file(users_file, preview=not quiet)
                
                # Show what operations will be performed
                if not quiet:
                    console.print(f"\n🎯 [bold magenta]Operations to perform:[/bold magenta]")
                    if assign_global_role:
                        console.print(f"   🔗 Assign global role: [cyan]{assign_global_role}[/cyan]")
                    if assign_org_role:
                        console.print(f"   🏢 Assign org role: [cyan]{assign_org_role}[/cyan] in org [cyan]{org_id}[/cyan]")
                    if remove_global_role:
                        console.print(f"   🗑️  Remove global role: [yellow]{remove_global_role}[/yellow]")
                    if remove_org_role:
                        console.print(f"   🗑️  Remove org role: [yellow]{remove_org_role}[/yellow] from org [yellow]{org_id}[/yellow]")
                    if assign_to_org:
                        console.print(f"   🏢 Assign to organization: [green]{org_id}[/green]")
                    if remove_from_org:
                        console.print(f"   🗑️  Remove from organization: [red]{org_id}[/red]")
                    
                    console.print(f"\n📊 [bold]Total users to process:[/bold] {len(user_identifiers)}")
                    
                    # Ask for confirmation (skip if --yes flag is used)
                    if not yes:
                        try:
                            if not Confirm.ask("\n❓ Do you want to proceed with these bulk operations?", default=False):
                                console.print("❌ [yellow]Operation cancelled by user[/yellow]")
                                return
                        except EOFError:
                            # Non-interactive mode, proceed automatically
                            console.print("\n🤖 [dim]Non-interactive mode detected, proceeding with bulk operations...[/dim]")
                    else:
                        console.print("\n✅ [dim]Confirmation skipped with --yes flag[/dim]")
                
                if not quiet:
                    console.print(f"\n🔍 [bold yellow]Resolving {len(user_identifiers)} users...[/bold yellow]")
                
                for identifier in user_identifiers:
                    # Try to determine if it's an email or user ID
                    if '@' in identifier:
                        user = exporter.get_user_by_email(identifier)
                    else:
                        user = exporter.get_user_by_id(identifier)
                    
                    if user:
                        target_users.append(user)
                    else:
                        console.print(f"⚠️  [yellow]User not found: {identifier}[/yellow]")
                
                if not quiet:
                    console.print(f"✅ Found {len(target_users)} out of {len(user_identifiers)} users")
            else:
                # Single user operation
                if user_id:
                    user = exporter.get_user_by_id(user_id)
                    query_type = f"ID: {user_id}"
                else:
                    user = exporter.get_user_by_email(email)
                    query_type = f"Email: {email}"
                
                if not user:
                    console.print(f"❌ [red]User not found with {query_type}[/red]")
                    sys.exit(1)
                
                target_users.append(user)
            
            if not target_users:
                console.print("❌ [red]No valid users found to process.[/red]")
                sys.exit(1)
            
            # Process each user
            total_success = 0
            total_users = len(target_users)
            
            for i, user in enumerate(target_users):
                target_user_id = user.get('user_id')
                user_email = user.get('email', 'N/A')
                
                if not quiet and total_users > 1:
                    console.print(f"\n🎯 [bold]Processing user {i+1}/{total_users}:[/bold] {user_email}")
                elif not quiet:
                    console.print(f"🎯 [bold]Target user:[/bold] {user_email} ({target_user_id})")
                
                user_success_count = 0
                user_actions = sum(1 for action in (role_actions + org_actions) if action)
                
                # Handle global role assignment
                if assign_global_role:
                    if not quiet:
                        console.print(f"🔗 [bold cyan]Assigning global role:[/bold cyan] {assign_global_role}")
                    if exporter.assign_global_role(target_user_id, assign_global_role):
                        console.print("✅ [green]Global role assigned successfully[/green]")
                        user_success_count += 1
                    else:
                        console.print("❌ [red]Failed to assign global role[/red]")
                
                # Handle organization role assignment
                if assign_org_role:
                    if not quiet:
                        console.print(f"🏢 [bold cyan]Assigning organization role:[/bold cyan] {assign_org_role} in org {org_id}")
                    if exporter.assign_organization_role(target_user_id, org_id, assign_org_role):
                        console.print("✅ [green]Organization role assigned successfully[/green]")
                        user_success_count += 1
                    else:
                        console.print("❌ [red]Failed to assign organization role[/red]")
                
                # Handle global role removal
                if remove_global_role:
                    if not quiet:
                        console.print(f"🗑️ [bold yellow]Removing global role:[/bold yellow] {remove_global_role}")
                    if exporter.remove_global_role(target_user_id, remove_global_role):
                        console.print("✅ [green]Global role removed successfully[/green]")
                        user_success_count += 1
                    else:
                        console.print("❌ [red]Failed to remove global role[/red]")
                
                # Handle organization role removal
                if remove_org_role:
                    if not quiet:
                        console.print(f"🗑️ [bold yellow]Removing organization role:[/bold yellow] {remove_org_role} from org {org_id}")
                    if exporter.remove_organization_role(target_user_id, org_id, remove_org_role):
                        console.print("✅ [green]Organization role removed successfully[/green]")
                        user_success_count += 1
                    else:
                        console.print("❌ [red]Failed to remove organization role[/red]")
                
                # Handle organization assignment
                if assign_to_org:
                    if not quiet:
                        console.print(f"🏢 [bold green]Assigning user to organization:[/bold green] {org_id}")
                    if exporter.assign_user_to_organization(target_user_id, org_id):
                        console.print("✅ [green]User assigned to organization successfully[/green]")
                        user_success_count += 1
                    else:
                        console.print("❌ [red]Failed to assign user to organization[/red]")
                
                # Handle organization removal
                if remove_from_org:
                    if not quiet:
                        console.print(f"🗑️ [bold red]Removing user from organization:[/bold red] {org_id}")
                    if exporter.remove_user_from_organization(target_user_id, org_id):
                        console.print("✅ [green]User removed from organization successfully[/green]")
                        user_success_count += 1
                    else:
                        console.print("❌ [red]Failed to remove user from organization[/red]")
                
                total_success += user_success_count
                
                if not quiet and total_users > 1:
                    console.print(f"📈 User {i+1} summary: {user_success_count}/{user_actions} actions completed")
            
            # Overall summary
            if not quiet:
                total_actions = total_users * user_actions
                console.print(f"\n📊 [bold]Overall Summary:[/bold] {total_success}/{total_actions} actions completed successfully")
                console.print(f"👥 Processed {total_users} user(s)")
                
                if total_success > 0 and total_users == 1:
                    console.print("💡 [dim]You can run with the same user options to see updated data:[/dim]")
                    console.print(f"   [dim]auth0-export --email {target_users[0].get('email', 'N/A')}[/dim]")
            
            return
        
        # Handle single user query
        if user_id or email:
            if not quiet:
                console.print("\n🔍 [bold yellow]Querying user...[/bold yellow]")
            
            # Get user by ID or email
            if user_id:
                user = exporter.get_user_by_id(user_id)
                query_type = f"ID: {user_id}"
            else:
                user = exporter.get_user_by_email(email)
                query_type = f"Email: {email}"
            
            if not user:
                console.print(f"❌ [red]User not found with {query_type}[/red]")
                sys.exit(1)
            
            if not quiet:
                console.print(f"✅ Found user: {user.get('email', 'N/A')}")
            
            # Get complete user data
            user_data = exporter.get_user_complete_data(user)
            
            # Handle output format
            if json_pretty and not quiet:
                # Display JSON in terminal
                console.print("\n📄 [bold cyan]User Data (JSON):[/bold cyan]")
                json_display = JSON.from_data(user_data)
                console.print(json_display)
            elif format == 'json':
                # Export to JSON file
                output_file = exporter.export_single_user_json(user_data, output)
                if not quiet:
                    console.print(f"\n✅ [bold green]User exported to JSON: {output_file}[/bold green]")
                else:
                    print(f"Export completed: {output_file}")
            else:
                # Display table format (no export prompts)
                if not quiet:
                    console.print("")
                    display_user_table(user_data)
                else:
                    # Quiet mode - just show essential info
                    print(f"User: {user.get('email', 'N/A')} ({user.get('user_id', 'N/A')})")
                    print(f"Organizations: {len(user_data['organizations'])}")
                    print(f"Global Roles: {len(user_data['global_roles'])}")
        
        else:
            # Full export mode
            if not quiet:
                console.print("\n📤 [bold yellow]Starting full export...[/bold yellow]")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeElapsedColumn(),
                    console=console,
                    expand=True
                ) as progress:
                    
                    # Add main task
                    export_task = progress.add_task("Exporting users...", total=100)
                    
                    def update_progress(current: int, total: int, current_user: str):
                        """Update progress bar with current status"""
                        percentage = (current / total) * 100 if total > 0 else 0
                        # Truncate email to consistent length (25 chars) to prevent bar jumping
                        truncated_user = current_user[:25].ljust(25) if len(current_user) <= 25 else current_user[:22] + "..."
                        progress.update(
                            export_task,
                            completed=percentage,
                            description=f"Processing {truncated_user}"
                        )
                    
                    if format == 'json':
                        output_file = exporter.export_to_json(output, progress_callback=update_progress)
                    else:
                        output_file = exporter.export_to_excel(output, progress_callback=update_progress)
                    
                    # Complete the progress
                    progress.update(export_task, completed=100, description="Export completed!")
            else:
                # Quiet mode - just run the export
                if format == 'json':
                    output_file = exporter.export_to_json(output)
                else:
                    output_file = exporter.export_to_excel(output)
            
            # Success message (no open file prompt)
            if not quiet:
                console.print("\n🎉 [bold green]Full export completed successfully![/bold green]")
                display_stats(exporter, output_file)
            else:
                print(f"Export completed: {output_file}")
            
    except KeyboardInterrupt:
        console.print("\n⚠️  [yellow]Export cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ [bold red]Export failed: {e}[/bold red]")
        if not quiet:
            console.print("\n💡 Try running with --setup to reconfigure credentials")
        sys.exit(1)

if __name__ == "__main__":
    main()