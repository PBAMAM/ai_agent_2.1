"""
Vonage Outbound Call Handler

This module provides functionality to make outbound phone calls using the Vonage API.
It handles call creation, webhook URLs, and call management.
"""

import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=".env")

# Configure logging
logger = logging.getLogger("vonage-caller")
logger.setLevel(logging.INFO)

try:
    from vonage import Client, CreateCallRequest
    VONAGE_AVAILABLE = True
except ImportError:
    VONAGE_AVAILABLE = False
    logger.warning("Vonage SDK not installed. Install with: pip install vonage")
    # Create a mock class for type hints
    class CreateCallRequest:
        pass
    class Client:
        pass


# ============================================================================
# Configuration
# ============================================================================

class VonageSettings:
    """Vonage API configuration settings."""
    
    # API Credentials
    VONAGE_API_KEY: str = os.getenv("VONAGE_API_KEY", "")
    VONAGE_API_SECRET: str = os.getenv("VONAGE_API_SECRET", "")
    
    # Phone Numbers
    VONAGE_PHONE_NUMBER: str = os.getenv("VONAGE_PHONE_NUMBER", "")
    
    # Webhook URLs (for call events and answer handling)
    # These should point to your webhook endpoints
    ANSWER_URL: str = os.getenv("VONAGE_ANSWER_URL", "https://your-domain.com/webhooks/vonage/answer")
    EVENT_URL: str = os.getenv("VONAGE_EVENT_URL", "https://your-domain.com/webhooks/vonage/event")
    
    # Optional: Status callback URL
    STATUS_URL: Optional[str] = os.getenv("VONAGE_STATUS_URL", None)


# ============================================================================
# Vonage Client Initialization
# ============================================================================

def get_vonage_client() -> Optional[Client]:
    """
    Initialize and return a Vonage client instance.
    
    Returns:
        Vonage Client instance if credentials are available, None otherwise
    """
    if not VONAGE_AVAILABLE:
        logger.error("Vonage SDK is not installed")
        return None
    
    settings = VonageSettings()
    
    if not settings.VONAGE_API_KEY or not settings.VONAGE_API_SECRET:
        logger.error("Vonage API credentials not configured. Set VONAGE_API_KEY and VONAGE_API_SECRET in .env")
        return None
    
    try:
        client = Client(key=settings.VONAGE_API_KEY, secret=settings.VONAGE_API_SECRET)
        logger.info("✅ Vonage client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Vonage client: {e}")
        return None


# ============================================================================
# Call Request Builder
# ============================================================================

def create_call_request(
    to_number: str,
    from_number: Optional[str] = None,
    answer_url: Optional[str] = None,
    event_url: Optional[str] = None,
    status_url: Optional[str] = None,
    **kwargs
) -> CreateCallRequest:
    """
    Create a Vonage call request with proper configuration.
    
    Args:
        to_number: The phone number to call (E.164 format, e.g., "+1234567890")
        from_number: The phone number to call from (defaults to VONAGE_PHONE_NUMBER)
        answer_url: URL for handling call answer events (defaults to VonageSettings.ANSWER_URL)
        event_url: URL for handling call events (defaults to VonageSettings.EVENT_URL)
        status_url: Optional URL for call status updates
        **kwargs: Additional parameters for CreateCallRequest
    
    Returns:
        CreateCallRequest object configured for making the call
    
    Example:
        >>> request = create_call_request(
        ...     to_number="+1234567890",
        ...     answer_url="https://api.example.com/webhooks/answer",
        ...     event_url="https://api.example.com/webhooks/event"
        ... )
        >>> response = client.voice.create_call(request)
    """
    settings = VonageSettings()
    
    # Use provided values or fall back to settings
    from_number = from_number or settings.VONAGE_PHONE_NUMBER
    answer_url = answer_url or settings.ANSWER_URL
    event_url = event_url or settings.EVENT_URL
    
    # Validate required fields
    if not to_number:
        raise ValueError("to_number is required")
    if not from_number:
        raise ValueError("from_number is required (set VONAGE_PHONE_NUMBER in .env)")
    if not answer_url:
        raise ValueError("answer_url is required (set VONAGE_ANSWER_URL in .env)")
    if not event_url:
        raise ValueError("event_url is required (set VONAGE_EVENT_URL in .env)")
    
    # Build the call request
    call_request = CreateCallRequest(
        to=[{"type": "phone", "number": to_number}],
        from_={"type": "phone", "number": from_number},
        answer_url=[answer_url],
        event_url=[event_url],
        **kwargs
    )
    
    # Add status URL if provided
    if status_url or settings.STATUS_URL:
        call_request.status_url = status_url or settings.STATUS_URL
    
    logger.info(f"📞 Call request created: {from_number} -> {to_number}")
    logger.debug(f"   Answer URL: {answer_url}")
    logger.debug(f"   Event URL: {event_url}")
    
    return call_request


# ============================================================================
# Call Management Functions
# ============================================================================

def make_call(
    to_number: str,
    from_number: Optional[str] = None,
    answer_url: Optional[str] = None,
    event_url: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Make an outbound phone call using Vonage API.
    
    Args:
        to_number: The phone number to call (E.164 format)
        from_number: The phone number to call from (optional)
        answer_url: URL for call answer webhook (optional)
        event_url: URL for call event webhook (optional)
        **kwargs: Additional parameters for CreateCallRequest
    
    Returns:
        Dictionary with call response data including call_uuid and status
    
    Example:
        >>> result = make_call(
        ...     to_number="+1234567890",
        ...     answer_url="https://api.example.com/webhooks/answer",
        ...     event_url="https://api.example.com/webhooks/event"
        ... )
        >>> print(f"Call UUID: {result['call_uuid']}")
        >>> print(f"Status: {result['status']}")
    """
    if not VONAGE_AVAILABLE:
        return {
            "success": False,
            "error": "Vonage SDK not installed. Install with: pip install vonage"
        }
    
    client = get_vonage_client()
    if not client:
        return {
            "success": False,
            "error": "Failed to initialize Vonage client. Check your API credentials."
        }
    
    try:
        # Create the call request
        call_request = create_call_request(
            to_number=to_number,
            from_number=from_number,
            answer_url=answer_url,
            event_url=event_url,
            **kwargs
        )
        
        # Make the call
        logger.info(f"📞 Initiating call to {to_number}...")
        response = client.voice.create_call(call_request)
        
        # Parse response
        result = {
            "success": True,
            "call_uuid": response.get("call_uuid"),
            "status": response.get("status"),
            "direction": response.get("direction"),
            "conversation_uuid": response.get("conversation_uuid"),
            "response": response
        }
        
        logger.info(f"✅ Call initiated successfully. UUID: {result['call_uuid']}")
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Failed to make call: {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }


def get_call_status(call_uuid: str) -> Dict[str, Any]:
    """
    Get the status of a call by its UUID.
    
    Args:
        call_uuid: The UUID of the call to check
    
    Returns:
        Dictionary with call status information
    """
    if not VONAGE_AVAILABLE:
        return {
            "success": False,
            "error": "Vonage SDK not installed"
        }
    
    client = get_vonage_client()
    if not client:
        return {
            "success": False,
            "error": "Failed to initialize Vonage client"
        }
    
    try:
        response = client.voice.get_call(call_uuid)
        return {
            "success": True,
            "status": response.get("status"),
            "call": response
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of the Vonage caller module.
    
    Before running, make sure you have:
    1. Installed vonage SDK: pip install vonage
    2. Set up your .env file with:
       - VONAGE_API_KEY=your_api_key
       - VONAGE_API_SECRET=your_api_secret
       - VONAGE_PHONE_NUMBER=your_vonage_number
       - VONAGE_ANSWER_URL=https://your-domain.com/webhooks/vonage/answer
       - VONAGE_EVENT_URL=https://your-domain.com/webhooks/vonage/event
    """
    
    # Example 1: Simple call
    print("Example 1: Making a simple call")
    result = make_call(
        to_number="+1234567890",  # Replace with actual number
        answer_url="https://your-domain.com/webhooks/vonage/answer",
        event_url="https://your-domain.com/webhooks/vonage/event"
    )
    print(f"Result: {result}")
    
    # Example 2: Create call request manually
    print("\nExample 2: Creating call request manually")
    request = create_call_request(
        to_number="+1234567890",
        answer_url="https://your-domain.com/webhooks/vonage/answer",
        event_url="https://your-domain.com/webhooks/vonage/event"
    )
    print(f"Call request created: {request}")
    
    # Example 3: Check call status
    if result.get("success") and result.get("call_uuid"):
        print(f"\nExample 3: Checking call status for {result['call_uuid']}")
        status = get_call_status(result["call_uuid"])
        print(f"Status: {status}")

