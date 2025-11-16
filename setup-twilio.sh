#!/bin/bash

# Twilio + LiveKit SIP Setup Script
# This script helps you set up inbound phone calls with Twilio and LiveKit

set -e

echo "=========================================="
echo "Twilio + LiveKit SIP Setup"
echo "=========================================="
echo ""

# Check if LiveKit CLI is installed
if ! command -v lk &> /dev/null; then
    echo "❌ LiveKit CLI not found!"
    echo ""
    echo "Please install it first:"
    echo "  macOS/Linux: curl -sSL https://get.livekit.io/cli | bash"
    echo "  Or: npm install -g livekit-cli"
    exit 1
fi

echo "✅ LiveKit CLI found"
echo ""

# Check if logged in
if ! lk whoami &> /dev/null; then
    echo "⚠️  Not logged in to LiveKit. Please run: lk login"
    exit 1
fi

echo "✅ Logged in to LiveKit"
echo ""

# Get trunk configuration
echo "Please provide the following information:"
echo ""

read -p "Trunk name (e.g., 'Twilio Inbound Trunk'): " TRUNK_NAME
read -p "SIP username (for Twilio authentication): " SIP_USERNAME
read -sp "SIP password (for Twilio authentication): " SIP_PASSWORD
echo ""
read -p "Twilio phone number (E.164 format, e.g., +1234567890): " PHONE_NUMBER

echo ""
echo "Creating SIP inbound trunk..."

# Create trunk JSON
TRUNK_JSON=$(cat <<EOF
{
  "trunk": {
    "name": "$TRUNK_NAME",
    "auth_username": "$SIP_USERNAME",
    "auth_password": "$SIP_PASSWORD",
    "numbers": ["$PHONE_NUMBER"]
  }
}
EOF
)

# Save to temporary file
TMP_TRUNK=$(mktemp)
echo "$TRUNK_JSON" > "$TMP_TRUNK"

# Create the trunk
TRUNK_OUTPUT=$(lk sip inbound create "$TMP_TRUNK" 2>&1)
TRUNK_EXIT_CODE=$?

if [ $TRUNK_EXIT_CODE -ne 0 ]; then
    echo "❌ Failed to create trunk:"
    echo "$TRUNK_OUTPUT"
    rm "$TMP_TRUNK"
    exit 1
fi

# Extract SIP endpoint from output (look for sip:... pattern)
SIP_ENDPOINT=$(echo "$TRUNK_OUTPUT" | grep -oE 'sip:[^[:space:]]+' | head -1)

if [ -z "$SIP_ENDPOINT" ]; then
    echo "⚠️  Could not extract SIP endpoint from output"
    echo "Please check the output above for the SIP endpoint URI"
    echo "It should look like: sip:your-trunk-id@sip.livekit.io"
else
    echo "✅ Trunk created successfully!"
    echo ""
    echo "📞 SIP Endpoint: $SIP_ENDPOINT"
    echo ""
fi

rm "$TMP_TRUNK"

# Create dispatch rule
echo "Creating dispatch rule..."

DISPATCH_JSON=$(cat <<EOF
{
  "dispatch_rule": {
    "rule": {
      "dispatchRuleIndividual": {
        "roomPrefix": "call-"
      }
    }
  }
}
EOF
)

TMP_DISPATCH=$(mktemp)
echo "$DISPATCH_JSON" > "$TMP_DISPATCH"

DISPATCH_OUTPUT=$(lk sip dispatch create "$TMP_DISPATCH" 2>&1)
DISPATCH_EXIT_CODE=$?

if [ $DISPATCH_EXIT_CODE -ne 0 ]; then
    echo "❌ Failed to create dispatch rule:"
    echo "$DISPATCH_OUTPUT"
    rm "$TMP_DISPATCH"
    exit 1
fi

echo "✅ Dispatch rule created successfully!"
rm "$TMP_DISPATCH"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure Twilio TwiML Bin:"
echo "   - Go to https://console.twilio.com/"
echo "   - Navigate to TwiML Bins"
echo "   - Create a new TwiML Bin with this content:"
echo ""
echo "   <?xml version=\"1.0\" encoding=\"UTF-8\"?>"
echo "   <Response>"
echo "     <Dial>"
echo "       <Sip username=\"$SIP_USERNAME\" password=\"$SIP_PASSWORD\">"
if [ -n "$SIP_ENDPOINT" ]; then
    echo "         $SIP_ENDPOINT"
else
    echo "         sip:your-trunk-id@sip.livekit.io"
fi
echo "       </Sip>"
echo "     </Dial>"
echo "   </Response>"
echo ""
echo "2. Configure your Twilio phone number:"
echo "   - Go to Phone Numbers → Manage → Active numbers"
echo "   - Click on your phone number"
echo "   - Under 'A Call Comes In', select the TwiML Bin you created"
echo "   - Save"
echo ""
if [ -n "$SIP_ENDPOINT" ]; then
    echo "3. SIP Endpoint to use in TwiML:"
    echo "   $SIP_ENDPOINT"
    echo ""
fi
echo "4. Start your agent:"
echo "   python assistant.py start"
echo ""
echo "5. Test by calling your Twilio phone number!"
echo ""

