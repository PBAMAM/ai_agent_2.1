#!/usr/bin/env python3
"""
Twilio + LiveKit SIP Setup Script (Python)
This script helps you set up inbound phone calls with Twilio and LiveKit using the LiveKit Python API.
"""

import asyncio
import os
import re
import sys
from typing import Optional

from dotenv import load_dotenv
from livekit import api

# Load environment variables
load_dotenv(dotenv_path=".env")


async def create_inbound_trunk(
    lkapi: api.LiveKitAPI,
    name: str,
    auth_username: str,
    auth_password: str,
    phone_number: str,
) -> api.SipInboundTrunk:
    """
    Create a SIP inbound trunk for Twilio.
    
    Args:
        lkapi: LiveKit API instance
        name: Trunk name
        auth_username: Username for SIP authentication
        auth_password: Password for SIP authentication
        phone_number: Twilio phone number in E.164 format
    
    Returns:
        Created SIP inbound trunk
    """
    print(f"Creating SIP inbound trunk '{name}'...")
    
    try:
        # Use request object format
        response = await lkapi.sip.create_sip_inbound_trunk(
            api.CreateSIPInboundTrunkRequest(
                trunk=api.SIPInboundTrunkInfo(
                    name=name,
                    auth_username=auth_username,
                    auth_password=auth_password,
                    numbers=[phone_number],
                )
            )
        )
        # Handle different response structures
        trunk = response.trunk if hasattr(response, 'trunk') else response
        print(f"✅ Successfully created trunk: {trunk.trunk_id}")
        print(f"   SIP Endpoint: {trunk.uri}")
        return trunk
    except Exception as e:
        print(f"❌ Failed to create trunk: {e}")
        raise


async def create_dispatch_rule(
    lkapi: api.LiveKitAPI,
    room_prefix: str = "call-",
) -> api.SipDispatchRule:
    """
    Create a dispatch rule to route each caller to a unique room.
    
    Args:
        lkapi: LiveKit API instance
        room_prefix: Prefix for room names (default: "call-")
    
    Returns:
        Created dispatch rule
    """
    print(f"Creating dispatch rule with room prefix '{room_prefix}'...")
    
    try:
        # Use request object format
        response = await lkapi.sip.create_sip_dispatch_rule(
            api.CreateSIPDispatchRuleRequest(
                rule=api.SIPDispatchRule(
                    dispatch_rule_individual=api.SIPDispatchRuleIndividual(
                        room_prefix=room_prefix
                    )
                )
            )
        )
        # Handle different response structures
        dispatch_rule = response.dispatch_rule if hasattr(response, 'dispatch_rule') else response
        print(f"✅ Successfully created dispatch rule: {dispatch_rule.dispatch_rule_id}")
        return dispatch_rule
    except Exception as e:
        print(f"❌ Failed to create dispatch rule: {e}")
        raise


async def list_existing_trunks(lkapi: api.LiveKitAPI) -> None:
    """List existing SIP trunks."""
    try:
        trunks = await lkapi.sip.list_sip_inbound_trunks()
        if trunks.items:
            print("\nExisting inbound trunks:")
            for trunk in trunks.items:
                print(f"  - {trunk.name} (ID: {trunk.trunk_id})")
                if hasattr(trunk, 'uri') and trunk.uri:
                    print(f"    SIP URI: {trunk.uri}")
        else:
            print("\nNo existing inbound trunks found.")
    except Exception as e:
        print(f"⚠️  Could not list existing trunks: {e}")


async def get_project_sip_uri(lkapi: api.LiveKitAPI) -> Optional[str]:
    """
    Get the SIP URI from the LiveKit project.
    This is the direct SIP URI you can use for VoIP calling.
    """
    try:
        # Try to get project info - the SIP URI is typically based on project ID
        # Note: This may vary depending on LiveKit API version
        # For now, we'll extract it from the URL if possible
        url = lkapi._url if hasattr(lkapi, '_url') else None
        if url:
            # Extract project identifier from URL
            # Format: wss://project-id.livekit.cloud
            match = re.search(r'wss://([^.]+)\.livekit\.cloud', url)
            if match:
                project_id = match.group(1)
                return f"sip:{project_id}.sip.livekit.cloud"
    except Exception:
        pass
    return None


async def main():
    """Main setup function."""
    print("=" * 60)
    print("Twilio + LiveKit SIP Setup (Python)")
    print("=" * 60)
    print()
    
    # Check environment variables
    livekit_url = os.getenv("LIVEKIT_URL")
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not all([livekit_url, livekit_api_key, livekit_api_secret]):
        print("❌ Missing required environment variables!")
        print()
        print("Please set the following in your .env file:")
        print("  LIVEKIT_URL=wss://your-livekit-server.com")
        print("  LIVEKIT_API_KEY=your-api-key")
        print("  LIVEKIT_API_SECRET=your-api-secret")
        sys.exit(1)
    
    print("✅ LiveKit credentials found in environment")
    print()
    
    # Initialize LiveKit API
    try:
        lkapi = api.LiveKitAPI(
            url=livekit_url,
            api_key=livekit_api_key,
            api_secret=livekit_api_secret,
        )
        print("✅ Connected to LiveKit API")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to LiveKit API: {e}")
        sys.exit(1)
    
    # Get project SIP URI for VoIP calling
    project_sip_uri = await get_project_sip_uri(lkapi)
    if project_sip_uri:
        print("📞 Your Project SIP URI (for direct VoIP calling):")
        print(f"   {project_sip_uri}")
        print()
        print("You can use this SIP URI directly in any VoIP client to call your agent!")
        print("No trunk setup needed for VoIP calls - just use this URI.")
        print()
        print("💡 Quick Tip: Run 'python configure_voip.py' for step-by-step VoIP client setup")
        print()
    
    # List existing trunks
    await list_existing_trunks(lkapi)
    print()
    
    # Get user input
    print("Please provide the following information:")
    print()
    
    trunk_name = input("Trunk name (e.g., 'Twilio Inbound Trunk'): ").strip()
    if not trunk_name:
        trunk_name = "Twilio Inbound Trunk"
    
    sip_username = input("SIP username (for Twilio authentication): ").strip()
    if not sip_username:
        print("❌ SIP username is required")
        sys.exit(1)
    
    import getpass
    sip_password = getpass.getpass("SIP password (for Twilio authentication): ").strip()
    if not sip_password:
        print("❌ SIP password is required")
        sys.exit(1)
    
    phone_number = input("Twilio phone number (E.164 format, e.g., +1234567890): ").strip()
    if not phone_number:
        print("❌ Phone number is required")
        sys.exit(1)
    
    # Ensure phone number starts with +
    if not phone_number.startswith("+"):
        phone_number = "+" + phone_number
    
    print()
    
    # Create trunk
    try:
        trunk = await create_inbound_trunk(
            lkapi=lkapi,
            name=trunk_name,
            auth_username=sip_username,
            auth_password=sip_password,
            phone_number=phone_number,
        )
        sip_endpoint = trunk.uri
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        await lkapi.aclose()
        sys.exit(1)
    
    print()
    
    # Create dispatch rule
    room_prefix = input("Room prefix for calls (default: 'call-'): ").strip()
    if not room_prefix:
        room_prefix = "call-"
    
    try:
        await create_dispatch_rule(lkapi, room_prefix=room_prefix)
    except Exception as e:
        print(f"\n⚠️  Trunk created but dispatch rule failed: {e}")
        print("You may need to create the dispatch rule manually.")
    
    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    
    # Display SIP URI for VoIP calling
    if sip_endpoint:
        print("📞 SIP URI for VoIP Calling:")
        print(f"   {sip_endpoint}")
        print()
        print("You can use this SIP URI to call directly from any VoIP client:")
        print("  - Linphone, Zoiper, MicroSIP, X-Lite, etc.")
        print("  - Configure your VoIP client with:")
        print(f"    SIP Server: sip.livekit.cloud")
        print(f"    Username/URI: {sip_endpoint}")
        print()
    
    print("Next steps for Twilio:")
    print()
    print("1. Configure Twilio TwiML Bin:")
    print("   - Go to https://console.twilio.com/")
    print("   - Navigate to TwiML Bins")
    print("   - Create a new TwiML Bin with this content:")
    print()
    print("   <?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    print("   <Response>")
    print("     <Dial>")
    print(f"       <Sip username=\"{sip_username}\" password=\"{sip_password}\">")
    print(f"         {sip_endpoint}")
    print("       </Sip>")
    print("     </Dial>")
    print("   </Response>")
    print()
    print("2. Configure your Twilio phone number:")
    print("   - Go to Phone Numbers → Manage → Active numbers")
    print("   - Click on your phone number")
    print("   - Under 'A Call Comes In', select the TwiML Bin you created")
    print("   - Save")
    print()
    print("3. Start your agent:")
    print("   python assistant.py start")
    print()
    print("4. Test by calling your Twilio phone number!")
    print()
    
    # Close API connection
    await lkapi.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

