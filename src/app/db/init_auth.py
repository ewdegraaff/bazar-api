#!/usr/bin/env python3
"""
Create and authenticate users in Supabase, storing their access token in .env.local.
Reads Supabase credentials from docker/server/.env.

NOTE: This script is for development purposes only. In production, users should
register through the normal flow without admin privileges.
"""
import os
import sys
import requests
import json
from pathlib import Path

from dotenv import load_dotenv

# Load environment from the correct docker/server/.env file
env_path = Path(__file__).resolve().parent.parent.parent.parent / "docker" / "server" / ".env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY]):
    raise EnvironmentError("SUPABASE_URL, SUPABASE_KEY, and SUPABASE_SERVICE_KEY must be set in docker/server/.env")

# Development users - these will not be created in production
USERS = [
    {
        "id": "f1b00781-2caf-46fd-a342-77f9494d545a",
        "email": "kelly@getbazar.app",
        "password": "AutomateEverything123!",
        "name": "Kelly",
        "system_role": "admin"
    },
    {
        "id": "e5cf73d9-877c-4ea5-accb-d46d4528e0a7",
        "email": "emanuel@getbazar.app",
        "password": "AutomateEverything123!",
        "name": "Emanuel",
        "system_role": "superadmin"
    }
]

def create_supabase_user(user: dict) -> None:
    """Create a user in Supabase with custom metadata and mark email as verified."""
    # Create new user using service role key to bypass email confirmation
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "email": user["email"],
        "password": user["password"],
        "user_metadata": {
            "user_id": user["id"],
            "name": user["name"],
            "system_role": user["system_role"],
            "plan_type": "Free"
        },
        "email_confirm": True
    }
    resp = requests.post(url, headers=headers, data=json.dumps(data))
    print(f"Create user response for {user['email']}: {resp.status_code} {resp.text}")
    if resp.status_code not in (200, 201, 409):  # 409 = already exists
        raise RuntimeError(f"Failed to create user {user['email']}: {resp.text}")
    
    print(f"✅ User {user['email']} created with service role key")

def authenticate_supabase_user(user: dict) -> str:
    """Authenticate a user and return the access token."""
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "email": user["email"],
        "password": user["password"]
    }
    resp = requests.post(url, headers=headers, data=json.dumps(data))
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to authenticate user {user['email']}: {resp.text}")
    return resp.json()["access_token"]

def write_token_to_env(email: str, token: str) -> None:
    """Write the access token to .env.local as USER_ACCESS_TOKEN_<EMAIL>."""
    env_path = Path(__file__).resolve().parent.parent / ".env.local"
    lines = []
    if env_path.exists():
        with env_path.open("r") as f:
            lines = f.readlines()
    # Remove any existing token lines for this email
    key = f"USER_ACCESS_TOKEN_{email.split('@')[0].upper()}"
    lines = [line for line in lines if not line.startswith(key + "=")]
    lines.append(f"{key}={token}\n")
    with env_path.open("w") as f:
        f.writelines(lines)
    print(f"📝 Token written to {env_path}")

def delete_supabase_user_by_email(email: str) -> None:
    """
    Delete a user in Supabase by email if exists.
    Uses the Admin API: first fetches user by email, then deletes by id.
    """
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    params = {"email": email}
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 200:
        users = resp.json().get("users", [])
        for user in users:
            user_id = user.get("id")
            if user_id:
                del_url = f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}"
                del_resp = requests.delete(del_url, headers=headers)
                if del_resp.status_code not in (200, 204):
                    print(f"Warning: Failed to delete user {email}: {del_resp.text}", file=sys.stderr)
    elif resp.status_code == 404:
        # No user found, nothing to delete
        return
    else:
        print(f"Warning: Failed to fetch user {email}: {resp.text}", file=sys.stderr)

def user_exists(email: str) -> bool:
    """Check if a user exists in Supabase by email."""
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    params = {"email": email}
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 200:
        users = resp.json().get("users", [])
        return any(u.get("email") == email for u in users)
    return False

def main() -> None:
    """First delete, then create, and finally authenticate users, storing the access token."""
    print("🚀 Initializing Supabase authentication for B2C users...")
    print(f"📁 Loading environment from: {env_path}")
    print(f"🔗 Supabase URL: {SUPABASE_URL}")
    
    try:
        for user in USERS:
            print(f"🔄 Processing {user['email']} ({user['system_role']})")
            delete_supabase_user_by_email(user["email"])
        
        for user in USERS:
            create_supabase_user(user)
            # Check if user exists after creation
            if user_exists(user["email"]):
                print(f"✅ User {user['email']} exists in Supabase after creation.")
            else:
                print(f"❌ User {user['email']} NOT found in Supabase after creation.")
            token = authenticate_supabase_user(user)
            write_token_to_env(user["email"], token)
            print(f"✅ {user['email']} created and authenticated")
        
        print("✅ Authentication initialization completed successfully!")
        
    except Exception as e:
        print(f"❌ Authentication initialization failed: {e}")
        raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ [ERROR] {e}", file=sys.stderr)
        sys.exit(1)
