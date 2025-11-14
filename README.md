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