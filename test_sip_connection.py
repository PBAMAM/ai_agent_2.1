#!/usr/bin/env python3
"""
SIP Connection Test Script
This script helps diagnose SIP connection issues.
"""

import os
import re
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")


def get_sip_uri():
    """Get SIP URI from environment."""
    livekit_url = os.getenv("LIVEKIT_URL", "")
    if livekit_url:
        match = re.search(r'wss://([^.]+)\.livekit\.cloud', livekit_url)
        if match:
            project_id = match.group(1)
            return f"sip:{project_id}.sip.livekit.cloud"
    return None


def main():
    print("=" * 60)
    print("SIP Connection Troubleshooting")
    print("=" * 60)
    print()
    
    # Check environment
    livekit_url = os.getenv("LIVEKIT_URL")
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    print("1. Checking Environment Variables:")
    if livekit_url:
        print(f"   ✅ LIVEKIT_URL: {livekit_url}")
    else:
        print("   ❌ LIVEKIT_URL: Not set")
    
    if livekit_api_key:
        print(f"   ✅ LIVEKIT_API_KEY: {'*' * 10}...{livekit_api_key[-4:]}")
    else:
        print("   ❌ LIVEKIT_API_KEY: Not set")
    
    if livekit_api_secret:
        print(f"   ✅ LIVEKIT_API_SECRET: {'*' * 10}...{livekit_api_secret[-4:]}")
    else:
        print("   ❌ LIVEKIT_API_SECRET: Not set")
    
    print()
    
    # Get SIP URI
    sip_uri = get_sip_uri()
    print("2. SIP URI Configuration:")
    if sip_uri:
        print(f"   ✅ SIP URI: {sip_uri}")
    else:
        print("   ❌ Could not determine SIP URI from LIVEKIT_URL")
        print("   Please check your .env file")
    
    print()
    print("3. VoIP Client Configuration:")
    print("   Make sure your VoIP client is configured with:")
    if sip_uri:
        print(f"   - SIP URI/Username: {sip_uri}")
    print("   - Server/Proxy: sip.livekit.cloud")
    print("   - Port: 5060")
    print("   - Transport: UDP or TCP")
    print("   - Password: (leave empty)")
    
    print()
    print("4. IMPORTANT - How to Dial:")
    print("   ⚠️  You cannot just dial '5' or any number!")
    print("   You need to dial the FULL SIP URI:")
    if sip_uri:
        print(f"   📞 Dial: {sip_uri}")
    else:
        print("   📞 Dial: sip:your-project-id.sip.livekit.cloud")
    print()
    print("   Some VoIP clients require different formats:")
    print("   - Try dialing: sip:your-project-id.sip.livekit.cloud")
    print("   - Or try: your-project-id.sip.livekit.cloud")
    print("   - Or check your client's 'Call' or 'Dial' option")
    
    print()
    print("5. Agent Status:")
    print("   Make sure your agent is running:")
    print("   python assistant.py start")
    print()
    print("   You should see logs like:")
    print("   - 'registered worker'")
    print("   - 'initializing process'")
    print("   - When a call connects: 'Connected to phone number'")
    
    print()
    print("6. Common Issues:")
    print("   ❌ Dialing just a number (like '5') won't work")
    print("   ✅ You must dial the full SIP URI")
    print()
    print("   ❌ Wrong server address")
    print("   ✅ Use: sip.livekit.cloud")
    print()
    print("   ❌ Agent not running")
    print("   ✅ Start with: python assistant.py start")
    print()
    print("   ❌ Firewall blocking SIP (port 5060)")
    print("   ✅ Check firewall settings")
    
    print()
    print("=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print()
    if sip_uri:
        print(f"1. Configure your VoIP client with SIP URI: {sip_uri}")
        print("2. In your VoIP client, dial the FULL SIP URI:")
        print(f"   {sip_uri}")
        print("3. Make sure your agent is running")
        print("4. The call should connect automatically")
    else:
        print("1. Check your .env file has LIVEKIT_URL set correctly")
        print("2. Get your SIP URI from LiveKit Cloud dashboard")
        print("3. Configure your VoIP client")
        print("4. Dial the full SIP URI (not just a number)")
    print()


if __name__ == "__main__":
    main()

