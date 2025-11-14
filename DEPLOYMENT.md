# Deployment Guide - Catalina Marketing Printer Support Agent

This guide covers multiple deployment options for your LiveKit telephony agent.

## Prerequisites

1. **LiveKit Server**: You need a LiveKit server instance (cloud or self-hosted)
2. **API Keys**: All required API keys configured
3. **Domain/URL**: For accessing the agent (if using web interface)

## Deployment Options

### Option 1: LiveKit Cloud (Recommended for Quick Start)

LiveKit Cloud is the easiest way to get started.

1. **Sign up for LiveKit Cloud**:
   - Go to https://cloud.livekit.io/
   - Create an account and project
   - Get your `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`

2. **Deploy Agent to Railway/Render/Fly.io**:
   - See Option 2, 3, or 4 below
   - Use your LiveKit Cloud credentials

### Option 2: Railway (Easiest)

Railway makes deployment very simple:

1. **Install Railway CLI**:
   ```bash
   npm i -g @railway/cli
   railway login
   ```

2. **Deploy**:
   ```bash
   railway init
   railway up
   ```

3. **Set Environment Variables** in Railway dashboard:
   - `LIVEKIT_URL`
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
   - `OPENAI_API_KEY`
   - `DEEPGRAM_API_KEY`
   - `ANTHROPIC_API_KEY` (optional)
   - `CARTESIA_API_KEY` (optional)

4. **Deploy**:
   ```bash
   railway deploy
   ```

### Option 3: Render

1. **Create a new Web Service** on Render:
   - Connect your GitHub repository
   - Select "Docker" as the environment
   - Build command: (auto-detected from Dockerfile)
   - Start command: `python assistant.py start`

2. **Set Environment Variables** in Render dashboard

3. **Deploy**: Render will automatically deploy on git push

### Option 4: Fly.io

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth login
   ```

2. **Create fly.toml** (see below)

3. **Deploy**:
   ```bash
   fly launch
   fly secrets set LIVEKIT_URL=... LIVEKIT_API_KEY=... etc.
   fly deploy
   ```

### Option 5: AWS/GCP/Azure (Production)

For production deployments, use container services:

**AWS (ECS/Fargate)**:
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t simetrix-callbot .
docker tag simetrix-callbot:latest <account>.dkr.ecr.us-east-1.amazonaws.com/simetrix-callbot:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/simetrix-callbot:latest

# Create ECS task definition and service
```

**Google Cloud Run**:
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/simetrix-callbot
gcloud run deploy simetrix-callbot \
  --image gcr.io/PROJECT_ID/simetrix-callbot \
  --platform managed \
  --region us-central1 \
  --set-env-vars LIVEKIT_URL=...,LIVEKIT_API_KEY=...
```

**Azure Container Instances**:
```bash
az acr build --registry <registry> --image simetrix-callbot:latest .
az container create \
  --resource-group <rg> \
  --name simetrix-callbot \
  --image <registry>.azurecr.io/simetrix-callbot:latest \
  --environment-variables LIVEKIT_URL=... LIVEKIT_API_KEY=...
```

### Option 6: Self-Hosted with Docker Compose

For running on your own server:

1. **Set up LiveKit Server** (if not using cloud):
   ```bash
   docker run -d \
     -p 7880:7880 \
     -p 7881:7881 \
     -p 7882:7882/udp \
     -p 50000-50100:50000-50100/udp \
     -e LIVEKIT_KEYS="your-api-key: your-api-secret" \
     livekit/livekit-server --dev
   ```

2. **Deploy Agent**:
   ```bash
   # Copy .env.example to .env and fill in values
   cp .env.example .env
   nano .env
   
   # Start with docker-compose
   docker-compose up -d
   ```

## Environment Variables

Create a `.env` file or set these in your deployment platform:

```env
# Required
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
OPENAI_API_KEY=your-openai-key
DEEPGRAM_API_KEY=your-deepgram-key

# Optional
ANTHROPIC_API_KEY=your-anthropic-key
GROQ_API_KEY=your-groq-key
CARTESIA_API_KEY=your-cartesia-key
```

## Testing Your Deployment

1. **Check Agent Status**:
   ```bash
   # If using docker
   docker logs simetrix-callbot-agent
   
   # Or check your platform's logs
   ```

2. **Test with LiveKit Playground**:
   - Go to https://agents-playground.livekit.io/
   - Enter your LiveKit credentials
   - Connect and test the agent

3. **Test Phone Call** (if SIP configured):
   - Use LiveKit's SIP integration
   - Call the assigned phone number

## Monitoring

### Health Checks

Add a health check endpoint (optional):

```python
# Add to assistant.py
from aiohttp import web

async def health_check(request):
    return web.json_response({"status": "healthy"})

app = web.Application()
app.router.add_get('/health', health_check)
```

### Logging

- Logs are automatically sent to stdout/stderr
- Most platforms capture these automatically
- Use your platform's logging dashboard

## Scaling

For production, consider:

1. **Horizontal Scaling**: Run multiple agent instances
2. **Load Balancing**: Use LiveKit's built-in load balancing
3. **Auto-scaling**: Configure based on queue length
4. **Monitoring**: Set up alerts for errors

## Troubleshooting

### Agent Not Connecting
- Verify `LIVEKIT_URL` is correct
- Check API keys are valid
- Ensure network connectivity

### TTS Errors
- Verify API keys (OpenAI, Cartesia, etc.)
- Check account credits/limits
- Review error logs

### High Latency
- Use region-close LiveKit servers
- Optimize model selection
- Consider caching

## Security Best Practices

1. **Never commit `.env` files**
2. **Use secrets management** (platform-native or external)
3. **Enable HTTPS** for all connections
4. **Rotate API keys** regularly
5. **Limit network access** to necessary services only

## Cost Optimization

1. **Use appropriate model sizes** (gpt-4.1-nano vs gpt-4)
2. **Monitor API usage** and set limits
3. **Use caching** where possible
4. **Scale down** during low-traffic periods

## Support

For issues:
- Check LiveKit documentation: https://docs.livekit.io/
- Review agent logs
- Check API provider status pages

