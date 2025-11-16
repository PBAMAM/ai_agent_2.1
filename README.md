# Simetrix Call Bot - Printer Support Assistant

A LiveKit-based telephony agent for handling printer support calls with integrated knowledge base and Claude AI support.

## Features

- **Printer Issue Knowledge Base**: Comprehensive database of printer issues and resolutions
- **Claude AI Integration**: Intelligent analysis of complex printer problems using Anthropic's Claude
- **Conversation Quality Monitoring**: Real-time sentiment analysis and conversation quality tracking
- **Automated Issue Resolution**: Lookup printer issues by customer description and provide step-by-step solutions

## Installation

First, create a virtual environment, update pip, and install the required packages:

```
$ python -m venv .venv
$ .venv\Scripts\activate  # On Windows
$ source .venv/bin/activate  # On macOS/Linux
$ python -m pip install --upgrade pip
$ pip install -r requirements.txt
```

## Environment Variables

You need to set up the following environment variables in a `.env` file:

```
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
GROQ_API_KEY=...
ANTHROPIC_API_KEY=...  # Optional: For Claude AI features
```

**Note**: `ANTHROPIC_API_KEY` is optional. If not provided, Claude features will be disabled but the printer knowledge base will still work.

## Usage

Then, run the assistant:

```
$ python assistant.py download-files
$ python assistant.py start
$ python assistant.py dev
$ python assistant.py console
$ python assistant.py start
```

Finally, you can load the [hosted playground](https://agents-playground.livekit.io/) and connect it.

## Inbound Phone Calls

This project supports receiving inbound phone calls through multiple methods:
- **VoIP Clients**: Call directly using the SIP URI from any SIP-compatible VoIP client
- **Twilio**: Route phone calls through Twilio to your LiveKit agent

### Calling from VoIP Clients

You can call your agent directly from any SIP-compatible VoIP application using the SIP URI from your LiveKit project. Calls are automatically routed to your LiveKit agent when it's running.

#### Get Your SIP URI

Your SIP URI is available in your LiveKit Cloud dashboard:
1. Go to your LiveKit Cloud project
2. Navigate to the project settings
3. Find the **SIP URI** field (format: `sip:your-project-id.sip.livekit.cloud`)

#### Configure VoIP Client

**For most SIP clients, you'll need:**
- **SIP Server/Proxy**: `sip.livekit.cloud`
- **SIP URI/Username**: Your full SIP URI (e.g., `sip:5lmt9badoqd.sip.livekit.cloud`)
- **Password**: Usually not required for direct SIP URI calls (unless you've configured authentication)

**Popular VoIP Clients:**

**1. Linphone (Desktop/Mobile)**
- Download from https://www.linphone.org/
- Add a new SIP account
- Username: Your SIP URI (e.g., `sip:5lmt9badoqd.sip.livekit.cloud`)
- Domain: `sip.livekit.cloud`
- Server: `sip.livekit.cloud`
- Transport: UDP or TCP

**2. Zoiper (Desktop/Mobile)**
- Download from https://www.zoiper.com/
- Add account → SIP Account
- Domain: `sip.livekit.cloud`
- Username: Your SIP URI
- Password: Leave empty (unless authentication is configured)

**3. MicroSIP (Windows)**
- Download from https://www.microsip.org/
- Account → Add Account
- Domain: `sip.livekit.cloud`
- Username: Your SIP URI
- Server: `sip.livekit.cloud`

**4. X-Lite/Bria (Desktop/Mobile)**
- Add SIP account
- Domain: `sip.livekit.cloud`
- Username: Your SIP URI
- Authorization User: Your SIP URI

**5. WebRTC (Browser)**
- Use LiveKit's web client or SIP.js
- Connect directly to the SIP URI

#### Quick Configuration Helper

Use the provided script to get step-by-step configuration instructions:

```bash
python configure_voip.py
```

This script will:
- Automatically detect your SIP URI from `.env`
- Show configuration steps for your VoIP client
- Generate configuration files if needed

#### Testing VoIP Calls

1. **Start your agent:**
   ```bash
   python assistant.py start
   ```

2. **Configure your VoIP client:**
   - Use the helper script: `python configure_voip.py`
   - Or manually configure using the settings below

3. **Make a call** - ⚠️ **IMPORTANT**: You must dial the FULL SIP URI, not just a number!
   - Dial: `sip:your-project-id.sip.livekit.cloud` (your full SIP URI)
   - Some clients: Enter the SIP URI in the "Call" or "Dial" field
   - The call will connect to LiveKit
   - LiveKit will create a room automatically
   - Your agent will join and start the conversation
   
   **Note**: Dialing just a number like "5" won't work. You need to dial the complete SIP URI.

4. **The agent will automatically:**
   - Detect the SIP participant
   - Create a room for the call
   - Connect and start the conversation
   - Handle the entire call flow

## Inbound Phone Calls with Twilio

This project supports receiving inbound phone calls through Twilio using LiveKit's native SIP integration. When someone calls your Twilio phone number, the call is automatically routed to your LiveKit agent.

### Prerequisites

- LiveKit server with SIP support enabled (LiveKit Cloud or self-hosted)
- LiveKit CLI installed (`lk` command)
- Twilio account with a phone number
- Agent running and connected to LiveKit

### Step 1: Install LiveKit CLI

If you haven't already, install the LiveKit CLI:

```bash
# macOS/Linux
curl -sSL https://get.livekit.io/cli | bash

# Or using npm
npm install -g livekit-cli
```

Authenticate with your LiveKit server:

```bash
lk login
```

### Step 2: Create LiveKit SIP Inbound Trunk

Create a JSON file for the inbound trunk configuration:

```bash
cat > inbound-trunk.json << EOF
{
  "trunk": {
    "name": "Twilio Inbound Trunk",
    "auth_username": "twilio-user",
    "auth_password": "your-secure-password-here",
    "numbers": ["+1234567890"]
  }
}
EOF
```

Replace:
- `twilio-user`: A username for Twilio to authenticate (can be any value)
- `your-secure-password-here`: A secure password (Twilio will use this to connect)
- `+1234567890`: Your Twilio phone number in E.164 format

Create the trunk:

```bash
lk sip inbound create inbound-trunk.json
```

The command will output the SIP endpoint URI. Save this - you'll need it for Twilio configuration. It will look something like:
```
sip:your-trunk-id@sip.livekit.io
```

### Step 3: Create LiveKit Dispatch Rule

Create a dispatch rule to route each caller to a unique room:

```bash
cat > dispatch-rule.json << EOF
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
```

Create the dispatch rule:

```bash
lk sip dispatch create dispatch-rule.json
```

This ensures each incoming call gets its own room with a name like `call-abc123`.

### Step 4: Configure Twilio TwiML

1. **Log in to Twilio Console**: Go to https://console.twilio.com/

2. **Create a TwiML Bin**:
   - Navigate to "TwiML Bins" in the left sidebar
   - Click "Create new TwiML Bin"
   - Name it "LiveKit SIP Connection"
   - Use the following TwiML (replace placeholders):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Dial>
    <Sip username="twilio-user" password="your-secure-password-here">
      sip:your-trunk-id@sip.livekit.io
    </Sip>
  </Dial>
</Response>
```

Replace:
- `twilio-user`: The username from Step 2
- `your-secure-password-here`: The password from Step 2
- `sip:your-trunk-id@sip.livekit.io`: The SIP endpoint URI from Step 2

3. **Save the TwiML Bin**

### Step 5: Configure Twilio Phone Number

1. In Twilio Console, go to "Phone Numbers" → "Manage" → "Active numbers"
2. Click on your phone number
3. Scroll to "Voice & Fax" section
4. Under "A Call Comes In", select "TwiML Bin"
5. Choose the TwiML Bin you created in Step 4
6. Click "Save"

### Step 6: Test the Setup

1. Make sure your agent is running:
   ```bash
   python assistant.py start
   ```

2. Call your Twilio phone number from any phone

3. The call should:
   - Connect to Twilio
   - Route to LiveKit via SIP
   - Create a room automatically
   - Connect to your agent
   - Start the conversation

### Troubleshooting

**Call doesn't connect:**
- Verify your agent is running and connected to LiveKit
- Check that the SIP trunk credentials match in both LiveKit and Twilio
- Verify the SIP endpoint URI is correct in Twilio TwiML
- Check LiveKit logs: `lk sip trunk list` to see trunk status

**Agent doesn't respond:**
- Ensure the agent worker is running: `python assistant.py start`
- Check agent logs for connection errors
- Verify LiveKit URL and API keys are correct in `.env`

**SIP authentication fails:**
- Double-check username and password match exactly in both places
- Ensure no extra spaces or special characters
- Try recreating the trunk with new credentials

**Can't find SIP commands:**
- Update LiveKit CLI: `npm install -g livekit-cli@latest`
- Verify you're logged in: `lk whoami`
- Check LiveKit server version supports SIP (requires LiveKit 1.5+)

### Helper Scripts

For convenience, you can use one of the provided setup scripts:

**Option 1: Python Script (Recommended)**
```bash
python setup_twilio.py
```

This script uses the LiveKit Python API and will:
- Read your LiveKit credentials from `.env`
- Prompt you for trunk configuration
- Create the SIP inbound trunk and dispatch rule
- Display the SIP endpoint and next steps

**Option 2: Shell Script (CLI-based)**
```bash
chmod +x setup-twilio.sh
./setup-twilio.sh
```

This script uses the LiveKit CLI and will prompt you for the required information and create the trunk and dispatch rule automatically.

## Printer Support Features

The assistant includes a comprehensive printer knowledge base with the following capabilities:

### Available Functions

1. **`lookup_printer_issue`**: Search for printer issues by customer description
   - Matches customer descriptions to known issues
   - Returns resolutions and step-by-step instructions

2. **`analyze_printer_issue_with_claude`**: Use Claude AI for complex issues
   - Intelligent analysis of unusual or complex problems
   - Provides recommendations when issues aren't in the knowledge base

### Supported Printer Issues

The knowledge base includes resolutions for:
- Paper jams and paper out errors
- Ink/toner problems and print quality issues
- Communication errors (PC No Comm)
- Power and connectivity issues
- Printer offline problems
- And more...

All issues include detailed troubleshooting steps and resolution instructions.

## Deployment

To deploy this agent online, see [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

### Quick Deploy Options

**Railway (Recommended for beginners)**:
```bash
npm i -g @railway/cli
railway login
railway init
railway up
```

**Render**:
1. Connect your GitHub repo
2. Select "Docker" environment
3. Set environment variables
4. Deploy

**Docker Compose** (Self-hosted):
```bash
docker-compose up -d
```

For more deployment options (AWS, GCP, Azure, Fly.io), see [DEPLOYMENT.md](DEPLOYMENT.md).

## Web Interface

A simple web interface is available to start/stop the agent:

```bash
python web_server.py
```

Then open your browser to `http://localhost:5000` to access the control panel.

The web interface provides:
- Start/Stop buttons for the agent
- Real-time status monitoring
- Live logs display
- Process information