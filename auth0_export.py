#!/usr/bin/env python3

import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
import pandas as pd
from dotenv import load_dotenv
from auth0.authentication import GetToken
from auth0.management import Auth0
import logging
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set debug level for troubleshooting
# Uncomment the line below to see debug messages
# logger.setLevel(logging.DEBUG)

class Auth0Exporter:
    def __init__(self):
        load_dotenv()
        
        self.domain = os.getenv('AUTH0_DOMAIN')
        self.client_id = os.getenv('AUTH0_CLIENT_ID')
        self.client_secret = os.getenv('AUTH0_CLIENT_SECRET')
        self.audience = os.getenv('AUTH0_AUDIENCE', f'https://{self.domain}/api/v2/')
        
        if not all([self.domain, self.client_id, self.client_secret]):
            raise ValueError("Missing required Auth0 credentials. Please check your .env file.")
        
        self.auth0 = self._get_management_client()
        
        # Rate limit configuration
        # Free/trial: 2 req/sec (burst 10), Paid: 15 req/sec (burst 50)
        # Default to conservative free tier limits, can be overridden via env var
        self.rate_limit_per_second = int(os.getenv('AUTH0_RATE_LIMIT_PER_SEC', '2'))
        self.last_request_time = 0
        self.min_time_between_requests = 1.0 / self.rate_limit_per_second
        
        logger.info(f"Rate limit configured: {self.rate_limit_per_second} requests/second")
        
    def _get_management_client(self) -> Auth0:
        """Initialize Auth0 Management API client"""
        get_token = GetToken(self.domain, self.client_id, self.client_secret)
        token = get_token.client_credentials(self.audience)
        return Auth0(self.domain, token['access_token'])
    
    def _rate_limit_wait(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_time_between_requests:
            sleep_time = self.min_time_between_requests - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _retry_with_backoff(self, func: Callable, *args, max_retries: int = 5, **kwargs) -> Any:
        """
        Execute a function with exponential backoff retry logic
        
        Args:
            func: The function to execute
            max_retries: Maximum number of retry attempts
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            The result of the function call
        """
        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                self._rate_limit_wait()
                
                # Execute the function
                result = func(*args, **kwargs)
                
                # Check if we got rate limit headers in response
                if hasattr(result, 'headers'):
                    remaining = result.headers.get('X-RateLimit-Remaining')
                    if remaining and int(remaining) < 5:
                        logger.warning(f"Rate limit warning: only {remaining} requests remaining")
                        # Add extra delay when getting close to limit
                        time.sleep(1)
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a rate limit error (429)
                if '429' in error_msg or 'rate limit' in error_msg.lower():
                    # Calculate exponential backoff with jitter
                    base_delay = 2 ** attempt
                    jitter = random.uniform(0, 1)
                    delay = base_delay + jitter
                    
                    logger.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries}). "
                                 f"Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
                    
                    # Double the minimum time between requests for next attempts
                    self.min_time_between_requests = min(self.min_time_between_requests * 1.5, 2.0)
                    
                elif attempt == max_retries - 1:
                    # Last attempt failed, re-raise the exception
                    logger.error(f"Failed after {max_retries} attempts: {error_msg}")
                    raise
                else:
                    # Other error, still retry with backoff
                    delay = 2 ** attempt + random.uniform(0, 1)
                    logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {error_msg}. "
                                 f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
        
        raise Exception(f"Failed after {max_retries} attempts")
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Fetch all users from Auth0"""
        logger.info("Fetching all users...")
        users = []
        page = 0
        per_page = 100
        
        while True:
            try:
                batch = self._retry_with_backoff(
                    self.auth0.users.list,
                    page=page,
                    per_page=per_page
                )
                if not batch.get('users'):
                    break
                users.extend(batch['users'])
                page += 1
                logger.info(f"Fetched {len(users)} users so far...")
            except Exception as e:
                logger.error(f"Error fetching users: {e}")
                break
                
        logger.info(f"Total users fetched: {len(users)}")
        return users
    
    def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get organizations for a specific user"""
        try:
            # The API returns a dict with 'organizations' key
            response = self._retry_with_backoff(
                self.auth0.users.list_organizations,
                user_id
            )
            orgs = response.get('organizations', []) if isinstance(response, dict) else response
            logger.debug(f"Organizations for user {user_id}: {len(orgs)} found")
            return orgs
        except Exception as e:
            logger.error(f"Error fetching organizations for user {user_id}: {e}")
            return []
    
    def get_user_organization_roles(self, user_id: str, org_id: str) -> List[Dict[str, Any]]:
        """Get roles for a user within a specific organization"""
        try:
            # The correct method is all_organization_member_roles
            roles = []
            page = 0
            while True:
                response = self._retry_with_backoff(
                    self.auth0.organizations.all_organization_member_roles,
                    org_id,
                    user_id,
                    page=page
                )
                if isinstance(response, dict) and 'roles' in response:
                    roles.extend(response['roles'])
                    if len(response['roles']) < 50:  # Default page size
                        break
                    page += 1
                else:
                    break
            return roles
        except Exception as e:
            logger.error(f"Error fetching roles for user {user_id} in org {org_id}: {e}")
            return []
    
    def get_user_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get global roles for a user (not organization-specific)"""
        try:
            # The correct method is list_roles
            response = self._retry_with_backoff(
                self.auth0.users.list_roles,
                user_id
            )
            roles = response.get('roles', []) if isinstance(response, dict) else response
            return roles
        except Exception as e:
            logger.error(f"Error fetching global roles for user {user_id}: {e}")
            return []
    
    def export_to_excel(self, output_filename: str = None) -> str:
        """Export all user data to Excel"""
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f'auth0_users_export_{timestamp}.xlsx'
        
        logger.info("Starting export process...")
        
        # Fetch all users
        users = self.get_all_users()
        
        # Prepare data for export
        export_data = []
        
        start_time = time.time()
        for i, user in enumerate(users):
            # Calculate and display progress
            if i > 0:
                elapsed = time.time() - start_time
                avg_time_per_user = elapsed / i
                remaining_users = len(users) - i
                eta_seconds = remaining_users * avg_time_per_user
                eta_minutes = eta_seconds / 60
                
                logger.info(f"Processing user {i+1}/{len(users)}: {user.get('email', 'N/A')} "
                          f"(ETA: {eta_minutes:.1f} minutes)")
            else:
                logger.info(f"Processing user {i+1}/{len(users)}: {user.get('email', 'N/A')}")
            
            # Basic user info
            user_data = {
                'User ID': user.get('user_id'),
                'Email': user.get('email'),
                'Name': user.get('name'),
                'Nickname': user.get('nickname'),
                'Picture': user.get('picture'),
                'Created At': user.get('created_at'),
                'Updated At': user.get('updated_at'),
                'Last Login': user.get('last_login'),
                'Login Count': user.get('logins_count', 0),
                'Email Verified': user.get('email_verified', False),
                'Blocked': user.get('blocked', False),
                'Connection': user.get('identities', [{}])[0].get('connection') if user.get('identities') else None,
                'Provider': user.get('identities', [{}])[0].get('provider') if user.get('identities') else None,
            }
            
            # Add user metadata
            user_metadata = user.get('user_metadata', {})
            app_metadata = user.get('app_metadata', {})
            
            # Flatten metadata
            for key, value in user_metadata.items():
                user_data[f'user_metadata.{key}'] = str(value)
            
            for key, value in app_metadata.items():
                user_data[f'app_metadata.{key}'] = str(value)
            
            # Get global roles
            global_roles = self.get_user_roles(user['user_id'])
            user_data['Global Roles'] = ', '.join([role.get('name', '') for role in global_roles])
            
            # Get organizations
            orgs = self.get_user_organizations(user['user_id'])
            logger.debug(f"User {user.get('email')} has {len(orgs)} organizations")
            
            if orgs:
                # Create a row for each organization the user belongs to
                for org in orgs:
                    org_data = user_data.copy()
                    org_data['Organization ID'] = org.get('id')
                    org_data['Organization Name'] = org.get('name')
                    org_data['Organization Display Name'] = org.get('display_name')
                    
                    # Get roles within this organization
                    org_roles = self.get_user_organization_roles(user['user_id'], org['id'])
                    org_data['Organization Roles'] = ', '.join([role.get('name', '') for role in org_roles])
                    
                    export_data.append(org_data)
            else:
                # User has no organizations - still add them to the export
                user_data['Organization ID'] = None
                user_data['Organization Name'] = None
                user_data['Organization Display Name'] = None
                user_data['Organization Roles'] = None
                export_data.append(user_data)
        
        # Create DataFrame and export to Excel
        df = pd.DataFrame(export_data)
        
        # Reorder columns for better readability
        column_order = [
            'User ID', 'Email', 'Name', 'Nickname', 'Email Verified', 'Blocked',
            'Organization ID', 'Organization Name', 'Organization Display Name',
            'Global Roles', 'Organization Roles',
            'Created At', 'Updated At', 'Last Login', 'Login Count',
            'Connection', 'Provider', 'Picture'
        ]
        
        # Add remaining columns (metadata fields)
        remaining_cols = [col for col in df.columns if col not in column_order]
        column_order.extend(remaining_cols)
        
        # Reorder DataFrame
        df = df[column_order]
        
        # Export to Excel with formatting
        with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Users', index=False)
            
            # Get the worksheet
            worksheet = writer.sheets['Users']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Calculate total time
        total_time = time.time() - start_time
        total_minutes = total_time / 60
        
        logger.info(f"Export completed successfully in {total_minutes:.1f} minutes!")
        logger.info(f"File saved as: {output_filename}")
        logger.info(f"Total users processed: {len(users)}")
        logger.info(f"Total rows exported: {len(export_data)}")
        
        return output_filename

def main():
    try:
        exporter = Auth0Exporter()
        output_file = exporter.export_to_excel()
        print(f"\nExport completed successfully!")
        print(f"Output file: {output_file}")
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()