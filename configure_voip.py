#!/usr/bin/env python3
"""
VoIP Client Configuration Helper
This script helps you configure your VoIP client to call your LiveKit agent.
"""

import os
import re
import sys
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=".env")


def get_sip_uri_from_env() -> Optional[str]:
    """Get SIP URI from environment variables or user input."""
    # Try to extract from LIVEKIT_URL
    livekit_url = os.getenv("LIVEKIT_URL", "")
    if livekit_url:
        # Extract project ID from URL
        # Format: wss://project-id.livekit.cloud
        match = re.search(r'wss://([^.]+)\.livekit\.cloud', livekit_url)
        if match:
            project_id = match.group(1)
            return f"sip:{project_id}.sip.livekit.cloud"
    
    return None


def print_linphone_config(sip_uri: str):
    """Print Linphone configuration instructions."""
    print("\n" + "=" * 60)
    print("Linphone Configuration")
    print("=" * 60)
    print("\n1. Open Linphone")
    print("2. Go to Settings → Accounts")
    print("3. Click '+' to add a new account")
    print("4. Select 'Use SIP account'")
    print("\nEnter the following:")
    print(f"   Username: {sip_uri}")
    print("   Domain: sip.livekit.cloud")
    print("   Password: (leave empty)")
    print("   Server: sip.livekit.cloud")
    print("   Transport: UDP or TCP")
    print("\n5. Save the account")
    print(f"6. Make a call by dialing the FULL SIP URI: {sip_uri}")
    print("   ⚠️  Do NOT dial just a number - you must dial the complete SIP URI!")
    print("   The call will connect to your LiveKit agent")


def print_zoiper_config(sip_uri: str):
    """Print Zoiper configuration instructions."""
    print("\n" + "=" * 60)
    print("Zoiper Configuration")
    print("=" * 60)
    print("\n1. Open Zoiper")
    print("2. Go to Settings → Accounts")
    print("3. Click 'Add Account' → 'SIP Account'")
    print("\nEnter the following:")
    print(f"   Display Name: LiveKit Agent")
    print(f"   User: {sip_uri}")
    print("   Domain: sip.livekit.cloud")
    print("   Password: (leave empty)")
    print("   Server: sip.livekit.cloud")
    print("   Port: 5060")
    print("   Transport: UDP")
    print("\n4. Save the account")
    print(f"5. Make a call by dialing the FULL SIP URI: {sip_uri}")
    print("   ⚠️  Do NOT dial just a number - you must dial the complete SIP URI!")
    print("   The call will connect to your LiveKit agent")


def print_microsip_config(sip_uri: str):
    """Print MicroSIP configuration instructions."""
    print("\n" + "=" * 60)
    print("MicroSIP Configuration")
    print("=" * 60)
    print("\n1. Open MicroSIP")
    print("2. Go to Account → Add Account")
    print("\nEnter the following:")
    print(f"   Account: {sip_uri}")
    print("   Domain: sip.livekit.cloud")
    print("   Username: (same as Account)")
    print("   Password: (leave empty)")
    print("   Server: sip.livekit.cloud")
    print("   Port: 5060")
    print("\n3. Click OK to save")
    print(f"4. Make a call by dialing the FULL SIP URI: {sip_uri}")
    print("   ⚠️  Do NOT dial just a number - you must dial the complete SIP URI!")
    print("   The call will connect to your LiveKit agent")


def print_xlite_config(sip_uri: str):
    """Print X-Lite/Bria configuration instructions."""
    print("\n" + "=" * 60)
    print("X-Lite / Bria Configuration")
    print("=" * 60)
    print("\n1. Open X-Lite or Bria")
    print("2. Go to Account Settings → Add Account")
    print("\nEnter the following:")
    print(f"   Display Name: LiveKit Agent")
    print(f"   User ID: {sip_uri}")
    print("   Domain: sip.livekit.cloud")
    print("   Password: (leave empty)")
    print(f"   Authorization User: {sip_uri}")
    print("   Server: sip.livekit.cloud")
    print("   Port: 5060")
    print("\n3. Save the account")
    print(f"4. Make a call by dialing the FULL SIP URI: {sip_uri}")
    print("   ⚠️  Do NOT dial just a number - you must dial the complete SIP URI!")
    print("   The call will connect to your LiveKit agent")


def print_generic_config(sip_uri: str):
    """Print generic SIP configuration."""
    print("\n" + "=" * 60)
    print("Generic SIP Client Configuration")
    print("=" * 60)
    print("\nFor any SIP-compatible VoIP client, use these settings:")
    print()
    print(f"SIP URI / Username: {sip_uri}")
    print("Domain: sip.livekit.cloud")
    print("Server / Proxy: sip.livekit.cloud")
    print("Port: 5060 (default)")
    print("Transport: UDP or TCP")
    print("Password: (usually not required)")
    print()
    print("To make a call:")
    print(f"1. Dial the FULL SIP URI: {sip_uri}")
    print("   ⚠️  IMPORTANT: You cannot dial just a number!")
    print("   You must dial the complete SIP URI shown above")
    print("2. The call will connect to your LiveKit agent")
    print("3. Your agent will automatically handle the conversation")


def generate_config_file(sip_uri: str, client_type: str):
    """Generate a configuration file for the VoIP client."""
    config_dir = "voip_configs"
    os.makedirs(config_dir, exist_ok=True)
    
    if client_type == "linphone":
        filename = f"{config_dir}/linphone_config.txt"
        content = f"""Linphone Configuration
====================

SIP Account Settings:
  Username: {sip_uri}
  Domain: sip.livekit.cloud
  Server: sip.livekit.cloud
  Password: (leave empty)
  Transport: UDP or TCP

Steps:
1. Open Linphone → Settings → Accounts
2. Add new SIP account with above settings
3. Save and make a call
"""
    elif client_type == "zoiper":
        filename = f"{config_dir}/zoiper_config.txt"
        content = f"""Zoiper Configuration
===================

SIP Account Settings:
  Display Name: LiveKit Agent
  User: {sip_uri}
  Domain: sip.livekit.cloud
  Server: sip.livekit.cloud
  Port: 5060
  Password: (leave empty)
  Transport: UDP

Steps:
1. Open Zoiper → Settings → Accounts
2. Add SIP Account with above settings
3. Save and make a call
"""
    else:
        filename = f"{config_dir}/generic_sip_config.txt"
        content = f"""Generic SIP Configuration
========================

SIP URI: {sip_uri}
Domain: sip.livekit.cloud
Server: sip.livekit.cloud
Port: 5060
Transport: UDP or TCP
Password: (usually not required)

Use these settings in any SIP-compatible VoIP client.
"""
    
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"\n✅ Configuration saved to: {filename}")


def main():
    """Main configuration function."""
    print("=" * 60)
    print("VoIP Client Configuration Helper")
    print("=" * 60)
    print()
    
    # Get SIP URI
    sip_uri = get_sip_uri_from_env()
    
    if not sip_uri:
        print("Could not automatically detect SIP URI from .env file.")
        print("Please enter your SIP URI manually.")
        print("(You can find it in your LiveKit Cloud dashboard)")
        print()
        sip_uri = input("Enter your SIP URI (e.g., sip:5lmt9badoqd.sip.livekit.cloud): ").strip()
        
        if not sip_uri:
            print("❌ SIP URI is required")
            sys.exit(1)
        
        # Ensure it starts with 'sip:'
        if not sip_uri.startswith("sip:"):
            sip_uri = f"sip:{sip_uri}"
    else:
        print(f"✅ Found SIP URI: {sip_uri}")
    
    print()
    print("Select your VoIP client:")
    print("1. Linphone")
    print("2. Zoiper")
    print("3. MicroSIP")
    print("4. X-Lite / Bria")
    print("5. Generic SIP Client")
    print("6. Show all configurations")
    print("7. Generate configuration file")
    print()
    
    choice = input("Enter your choice (1-7): ").strip()
    
    if choice == "1":
        print_linphone_config(sip_uri)
    elif choice == "2":
        print_zoiper_config(sip_uri)
    elif choice == "3":
        print_microsip_config(sip_uri)
    elif choice == "4":
        print_xlite_config(sip_uri)
    elif choice == "5":
        print_generic_config(sip_uri)
    elif choice == "6":
        print_linphone_config(sip_uri)
        print_zoiper_config(sip_uri)
        print_microsip_config(sip_uri)
        print_xlite_config(sip_uri)
        print_generic_config(sip_uri)
    elif choice == "7":
        print("\nSelect client type for config file:")
        print("1. Linphone")
        print("2. Zoiper")
        print("3. Generic")
        file_choice = input("Enter choice (1-3): ").strip()
        
        client_map = {"1": "linphone", "2": "zoiper", "3": "generic"}
        client_type = client_map.get(file_choice, "generic")
        generate_config_file(sip_uri, client_type)
    else:
        print("Invalid choice. Showing generic configuration:")
        print_generic_config(sip_uri)
    
    print()
    print("=" * 60)
    print("Important: Make sure your agent is running!")
    print("=" * 60)
    print()
    print("Before making a call, start your agent:")
    print("  python assistant.py start")
    print()
    print("Then configure your VoIP client and make a call.")
    print("The call will automatically route to your LiveKit agent.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

