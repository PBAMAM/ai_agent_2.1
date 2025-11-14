"""
Professional Telephony Agent for Printer Support
Catalina Marketing - Printer Support Specialist Agent

This module provides a LiveKit-based telephony agent for handling printer support calls
with conversation analysis, knowledge base integration, and AI-powered assistance.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Set, Callable
from functools import lru_cache

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
    RoomInputOptions,
    mcp,
)
from livekit.plugins import (
    groq,
    silero,
    cartesia,
    openai,
    deepgram,
    noise_cancellation,
)
from dotenv import load_dotenv

from conversation_analyzer import (
    ConversationAnalyzer,
    ConversationMetrics,
    ConversationQuality,
)
from printer_knowledge_base import PrinterKnowledgeBase, PrinterIssue

# Load environment variables
load_dotenv(dotenv_path=".env")

# ============================================================================
# Constants and Configuration
# ============================================================================

# Logging configuration
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

analyzer_logger = logging.getLogger("conversation-analyzer")
analyzer_logger.setLevel(logging.INFO)

# Suppress noisy warnings from external libraries
logging.getLogger("livekit.plugins.deepgram").setLevel(logging.ERROR)
logging.getLogger("livekit.agents.mcp").setLevel(logging.ERROR)
logging.getLogger("opentelemetry.attributes").setLevel(logging.ERROR)

# Agent configuration
DEFAULT_PHONE_NUMBER = "1123456"
TRANSCRIPT_MIN_LENGTH = 3
TRANSCRIPT_CACHE_SIZE = 100
MONITORING_INTERVAL = 0.5  # seconds
STATUS_UPDATE_INTERVAL = 10  # iterations
AUDIO_THRESHOLD = 0.7
MAX_ISSUE_MATCHES = 3

# Goodbye detection keywords (compiled regex for performance)
GOODBYE_KEYWORDS: Set[str] = {
    "goodbye", "bye", "thanks", "thank you", "have a good day",
    "talk to you later", "see you", "take care", "that's all",
    "all set", "we're done", "i'm done", "all good", "sounds good",
}
GOODBYE_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(kw) for kw in GOODBYE_KEYWORDS) + r')\b',
    re.IGNORECASE
)

# Transcript extraction patterns (compiled for performance)
USER_TRANSCRIPT_PATTERN = re.compile(
    r'"user_transcript"\s*:\s*"([^"]+)"',
    re.IGNORECASE
)

# MCP Server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp/")

# Claude AI configuration
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
CLAUDE_MAX_TOKENS = 1000

# ============================================================================
# Anthropic/Claude Client Initialization
# ============================================================================

ANTHROPIC_AVAILABLE = False
claude_client: Optional[Any] = None

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            claude_client = Anthropic(api_key=api_key)
            logger.info("✅ Claude (Anthropic) client initialized successfully")
        except Exception as e:
            logger.debug(f"Failed to initialize Claude client: {e}")
    else:
        logger.debug("Claude AI not configured (ANTHROPIC_API_KEY not set)")
except ImportError:
    logger.debug("Anthropic SDK not available. Claude features will be disabled.")


# ============================================================================
# Configuration Classes
# ============================================================================

@dataclass
class AgentConfig:
    """Configuration for the agent's behavior and personality."""
    name: str = "Kim"
    company: str = "Catalina Marketing"
    role: str = "Printer Support Specialist"
    personality: str = "friendly, helpful, patient, and technically knowledgeable, as human as possible"


@dataclass
class SessionConfig:
    """Configuration for the agent session."""
    llm_model: str = "gpt-4o-mini"
    tts_model: str = "sonic-3"
    tts_language: str = "en"
    tts_voice: str = "f9836c6e-a0bd-460e-9d3c-f7299fa60f94"
    audio_threshold: float = AUDIO_THRESHOLD
    


# ============================================================================
# Transcript Interceptor (Optimized)
# ============================================================================

class TranscriptInterceptor(logging.Handler):
    """
    Optimized logging handler for intercepting and extracting user transcripts.
    
    Uses compiled regex patterns for better performance and thread-safe operations.
    """
    
    def __init__(self, max_size: int = TRANSCRIPT_CACHE_SIZE):
        super().__init__()
        self.transcripts: List[str] = []
        self.max_size = max_size
        self._lock = asyncio.Lock()
    
    def emit(self, record: logging.LogRecord) -> None:
        """Extract user transcript from log record."""
        try:
            msg = self.format(record)
            msg_lower = msg.lower()
            
            # Quick check before regex
            if "user_transcript" not in msg_lower and "received user transcript" not in msg_lower:
                return
            
            # Use compiled regex for extraction
            match = USER_TRANSCRIPT_PATTERN.search(msg)
            if match:
                transcript = match.group(1)
                if transcript and len(transcript.strip()) >= TRANSCRIPT_MIN_LENGTH:
                    self._add_transcript(transcript)
            else:
                # Fallback: try simple string extraction
                if "user_transcript" in msg:
                    parts = msg.split("user_transcript")
                    if len(parts) > 1:
                        for quote_char in ['"', "'"]:
                            if quote_char in parts[1]:
                                try:
                                    transcript = parts[1].split(quote_char)[1]
                                    if transcript and len(transcript.strip()) >= TRANSCRIPT_MIN_LENGTH:
                                        self._add_transcript(transcript)
                                        break
                                except (IndexError, ValueError):
                                    continue
        except Exception as e:
            logger.debug(f"Error in transcript interceptor: {e}")
    
    def _add_transcript(self, transcript: str) -> None:
        """Add transcript to list with size management."""
        self.transcripts.append(transcript.strip())
        if len(self.transcripts) > self.max_size:
            self.transcripts.pop(0)


# ============================================================================
# Global State Management
# ============================================================================

class AgentState:
    """Manages global agent state in a thread-safe manner."""
    
    def __init__(self):
        self.phone_number: str = DEFAULT_PHONE_NUMBER
        self.analyzer: Optional[ConversationAnalyzer] = None
        self.printer_kb: PrinterKnowledgeBase = PrinterKnowledgeBase()
        self.analyzed_transcripts: Set[str] = set()
        self._transcript_cache_size = TRANSCRIPT_CACHE_SIZE
        self.job_context: Optional[JobContext] = None
    
    def add_analyzed_transcript(self, transcript: str) -> None:
        """Add transcript to analyzed set with cache management."""
        self.analyzed_transcripts.add(transcript)
        if len(self.analyzed_transcripts) > self._transcript_cache_size:
            # Clear oldest entries (simple FIFO approximation)
            self.analyzed_transcripts.clear()
    
    def clear_analyzed_transcripts(self) -> None:
        """Clear analyzed transcripts cache."""
        self.analyzed_transcripts.clear()


# Global state instance
agent_state = AgentState()

# Initialize transcript interceptor
transcript_interceptor = TranscriptInterceptor()
livekit_logger = logging.getLogger("livekit.agents")
livekit_logger.addHandler(transcript_interceptor)


# ============================================================================
# Agent Configuration Builder
# ============================================================================

def build_agent_config() -> Dict[str, Any]:
    """
    Build comprehensive agent configuration dictionary.
    
    Returns:
        Dictionary containing all agent configuration settings.
    """
    config = AgentConfig()
    
    return {
        "agent_info": {
            "name": config.name,
            "company": config.company,
            "role": config.role,
            "personality": config.personality,
        },
        "conversation_guidelines": {
            "greeting_style": "Thank you for calling Catalina Marketing support. My name is Kim. How can I help you today?",
            
            "introduce_yourself_with_name": "My name is Kim, and I'm here to help you resolve your printer issue today.",
            
            "call_flow": {
                "step_1_greeting": "After greeting, if customer mentions printer issue, say: 'I understand you're having an issue with your printer. I'll be happy to help you with that. Before we begin, let me verify some information.'",
                "step_2_customer_verification": "Ask for phone number: 'Could you please confirm your phone number for me?' After they provide it, repeat it back: 'Thank you. I have [repeat phone number]. Is that correct?' Wait for confirmation. Then ask: 'Great. And can you confirm your address?' After they provide it, repeat it back: 'Perfect. I have [repeat address]. Is that correct?' Wait for confirmation.",
                "step_3_device_verification": "Ask for serial number: 'Now, can you please provide me with the serial number of your printer? You can usually find this on the back or bottom of the device.' After they provide it, repeat it back: 'Thank you. That's serial number [repeat serial number]. Is that correct?' Wait for confirmation.",
                "step_4_issue_diagnosis": "Ask about the issue: 'Now, can you tell me what issue you're experiencing with your printer?' Listen for: blinking lights, paper jams, not printing, error messages, connection issues. Then say: 'I understand. You mentioned [summarize issue]. Can you tell me when this problem started?' After response, ask: 'Thank you for that information. And what color is the light that's blinking on your printer?'",
                "step_5_troubleshooting": "Use lookup_printer_issue to find the appropriate troubleshooting steps. Walk through steps ONE at a time, waiting for confirmation after each step.",
                "step_6_verification": "After troubleshooting, verify: 'Excellent! I'm glad we were able to resolve that for you. Let's do a quick test to make sure everything is working properly. Can you try printing a test page for me?' Wait for customer to print. Ask: 'Great! Did the test page print successfully?' If successful: 'Perfect! Your printer is now back online and working properly.' If not: 'I see. Let's try [alternative troubleshooting step] or I can escalate this to our technical team for further assistance.'",
                "step_7_additional_issues": "Ask: 'Is there anything else I can help you with today?' If they mention another issue, help with that. If they mention billing: 'I understand you're having a billing issue. Let me look into that for you. Can you tell me more about the billing concern?'",
                "step_8_closing": "If no additional issues: 'I'm glad I could help you today. Just to recap, we've successfully resolved your printer issue by [summarize resolution]. Your printer should now be working properly.' Then: 'Before we end this call, I want to remind you that you can reach our support team anytime if you need assistance. Is there anything else I can clarify for you?' After response: 'Thank you for calling Catalina Marketing support. Have a great day!'"
            },

            "printer_support_focus": "You are a printer support specialist for Catalina Marketing printers (CMC6, CMC7, CMC8, CMC9). Your mission is to help store staff troubleshoot and resolve printer issues remotely with patience, clarity, and step-by-step instructions.",

            "printer_issue_handling": {
            "listen_carefully": "Ask deeper questions about the issue: Ask which line the printer is on (example: Line 1, Line 5). Ask if there are blinking lights, noises, errors, paper jams, out of paper, ink issues, blank/faded prints, or communication errors.",
            "use_knowledge_base": "ALWAYS use lookup_printer_issue before giving any troubleshooting instruction.",
            "follow_steps": "Follow troubleshooting steps exactly as written. Give ONE step at a time, and wait for POC confirmation before moving on.",
            "provide_resolution": "Guide the POC step-by-step. Use simple language and be patient.",
            "verify_resolution": "After troubleshooting, verify the printer status, confirm prints are working, or assist with print quality checks.",
            "call_recording": "Remember that printer support calls may be recorded for quality and training.",
            "test_prints": "Do NOT send test prints unless the POC specifically asks for them.",
            "cleaning_cycle": "If print quality issues occur or blinking light issue, ask: 'Okay, based on what you've described, it sounds like your printer may need a cleaning cycle. I'm going to walk you through this process. It will take about one minute. Are you ready?' Wait for confirmation. Then guide them: 'First, locate the [specific button] on your printer. Can you see it?' Wait for confirmation. 'Now, press and hold that button for about 3 seconds until the light changes. Let me know when you've done that.' Wait for customer action. 'Perfect. You're doing great. Now the printer should begin its cleaning cycle. This will take about a minute. The light may blink during this process - that's normal. Let's wait for it to complete.' While waiting: 'While we're waiting, I want to let you know that this cleaning cycle helps maintain your printer's print quality and can resolve many common issues.' After cleaning cycle: 'Okay, the cleaning cycle should be complete now. Can you check the printer? The light should now be solid green and no longer blinking. What do you see?'",
            "dispatch_escalation": "If remote troubleshooting fails, offer escalation. Ask: 'I can escalate this ticket and send a technician to your location if you'd like. Would you like me to arrange a tech visit?'"
            },

            "communication_with_poc": {
            "be_clear_and_patient": "Use friendly, simple language. Speak slowly and clearly.",
            "confirm_understanding": "Ask 'Do you see that?', 'Can you confirm for me?', 'Let me know when you're ready for the next step.'",
            "provide_encouragement": "Say things like 'You're doing great', 'Nice job', 'Perfect, thank you', 'You're doing great, we're almost there'.",
            "handle_unwilling_poc": "If the POC refuses or cannot assist, follow the standard Unwilling POC process.",
            "store_specific_handling": "Ask early: 'Are you calling from Walgreens, Kroger, Meijer, HEB, or another store?' Some retailers have special procedures.",
            "empathy_statements": [
                "I understand how frustrating this must be.",
                "I appreciate your patience while we work through this.",
                "You're doing great, we're almost there.",
                "I understand how frustrating this can be.",
                "Don't worry, we'll get this resolved for you."
            ],
            "reassurance_statements": [
                "This is a common issue and we can fix it quickly.",
                "I'll walk you through this step by step.",
                "Don't worry, I'm here to help.",
                "This is a common issue and we can fix it quickly."
            ],
            "transition_phrases": [
                "Let me take a look at that for you.",
                "Here's what we're going to do...",
                "Perfect, let's move on to the next step."
            ]
            },

            "troubleshooting_approach": {
            "start_with_basics": "Begin with the simple checks: is the printer powered on, lights active, cables connected, any visible error?",
            "one_step_at_a_time": "Give ONE step at a time and wait for confirmation.",
            "wait_for_confirmation": "Ask 'Have you done that?', 'Let me know when that step is complete.'",
            "do_not_rush": "Never give multiple steps at once. Be patient.",
            "systematic_troubleshooting": "Move from simple to advanced troubleshooting while documenting findings.",
            "document_findings": "Note everything: problem description, steps performed, POC responses, results.",
            "verify_before_closing": "Confirm the issue is resolved before closing. If print quality was involved, ensure it’s acceptable."
            },

            "objection_handling": {
            "poc_busy": "If POC is busy: 'I understand. Would you like me to call back in 30 minutes or at a better time?'",
            "poc_uncomfortable": "If POC is uncomfortable: 'I can explain it more simply, or if you'd prefer, we can look at dispatching a technician.'",
            "technical_difficulty": "Break steps down further: 'No problem, let's take this slowly. Here's the next small step...'",
            "customer_frustrated": "If customer seems frustrated: Use empathetic language like 'I understand how frustrating this can be...', reassure them with 'Don't worry, we'll get this resolved for you.', be patient and slow down explanations.",
            "cannot_locate_parts": "If customer cannot locate buttons/parts: Provide detailed descriptions like 'It should be on the right side, near the top...', offer to email instructions with pictures, be patient and offer alternative ways to identify components.",
            "technical_steps_fail": "If technical steps fail: Offer alternative solution, provide option to schedule technician visit, escalate to senior support if needed.",
            "requires_physical_repair": "If issue requires physical repair: Explain warranty status, provide options (in-home service, mail-in repair, replacement), set expectations on timeline."
            },

            "resolution_documentation": {
            "equip_resolution_cat": "Always select Equipment Resolution Category: Printer.",
            "equip_resolution_method": "Document the exact resolution (Loaded Paper, Cleared Jam, Cleaning Cycle, Power Reset, Replaced Ribbon, PC Reboot, etc.).",
            "equip_status": "Set status to 'Resolved - Remote (First, Second, Third Call)' when resolved remotely.",
            "ticket_notes": "Include store location, line number, issue description, steps taken, and final results."
            }
        },
        "conversation_style": {
            "tone": "friendly and professional, patient and reassuring, clear and articulate. Use warm, helpful tone with slight variation in pitch to maintain engagement. Be professional but conversational.",
            "pace": (
                "Moderate speed - not too fast when giving instructions. "
                "Pause after questions to allow customer response (wait 3-5 seconds). "
                "Slow down for technical steps. "
                "SLOW and methodical - present ONE step, WAIT for confirmation, then proceed. "
                "Give the customer time to physically complete each action. Never rush or give "
                "multiple steps at once."
            ),
            "language": (
                "clear, simple language - avoid technical jargon unless necessary, and "
                "explain technical terms when used"
            ),
            "empathy": (
                "acknowledge that troubleshooting can be frustrating and show understanding. "
                "Use empathetic statements when customer seems frustrated or confused."
            ),
            "transparency": (
                "be honest about what you know and don't know. If you're unsure, consult "
                "the knowledge base or escalate appropriately"
            ),
            "respect": (
                "always respect the customer's time and situation. If they need to attend to "
                "customers, offer to call back. If there's background noise, ask if they need a moment."
            ),
            "listening_triggers": {
                "customer_frustration": "Switch to more empathetic tone",
                "customer_confusion": "Slow down and repeat instructions",
                "customer_multitasking": "Offer to wait or call back",
                "background_noise": "Ask if they need a moment"
            }
        },
        "conversation_flow": [
            "step_1_greeting_and_issue_identification",
            "step_2_customer_verification_phone_and_address",
            "step_3_account_device_verification_serial_number",
            "step_4_issue_diagnosis",
            "step_5_troubleshooting_steps",
            "step_6_verification",
            "step_7_additional_issues_check",
            "step_8_closing",
        ],
        "important_notes": [
            "⚠️ CRITICAL: Follow the 8-step call flow in order: Greeting → Customer Verification → Device Verification → Issue Diagnosis → Troubleshooting → Verification → Additional Issues → Closing",
            "⚠️ CRITICAL: Give ONE troubleshooting step at a time, then STOP and WAIT for confirmation",
            "⚠️ CRITICAL: Do NOT list multiple steps in a row - present step 1, wait for completion, then present step 2",
            "⚠️ CRITICAL: After each step, explicitly ask 'Have you done that?' or 'Did that work?' before continuing",
            "⚠️ CRITICAL: Always confirm important information by repeating it back (phone numbers, addresses, serial numbers)",
            "⚠️ CRITICAL: Allow 3-5 seconds after each question for customer response",
            "Always be respectful of the customer's time and situation - they may be busy with customers",
            "If the customer seems busy or distracted, offer to call back later",
            "Never rush the customer through troubleshooting steps - accuracy is more important than speed",
            "Be patient and methodical - wait for the customer to physically complete each action",
            "Be honest about what you can and cannot do remotely",
            "Use natural conversation flow - don't sound like you're reading from a script",
            "Speak naturally and conversationally - don't mention that you're following a script or reading instructions",
            "IMPORTANT: When the user says goodbye, thanks you, or indicates the conversation is complete, "
            "you MUST call the end_conversation function to properly close the job",
            "For outbound calls (system alerts), test coupons are only sent if the customer requests them",
            "Always verify printer status and print quality before closing a ticket",
            "Follow store-specific handling procedures when applicable (Walgreens, Kroger, Meijer, HEB, etc.)",
            "If customer interrupts, acknowledge and adjust flow accordingly",
            "If customer answer is unclear, politely ask them to repeat",
            "Document all actions taken during the call for future reference",
            "Offer to send summary email with troubleshooting steps if helpful",
        ],
        "escalation_criteria": [
            "Escalate to human agent if customer becomes very frustrated or angry",
            "Escalate if technical issue cannot be resolved after 2-3 attempts",
            "Escalate if customer requests to speak to a supervisor",
            "Escalate if issue requires account changes or refunds",
            "Escalate if complex technical issue outside of script scope",
            "Escalate if safety concern or potential equipment damage",
        ],
        "success_metrics": {
            "first_call_resolution": "Aim to resolve issue in single call",
            "average_handle_time": "Target 3-5 minutes",
            "customer_satisfaction": "Seek positive feedback on resolution",
            "efficiency": "Minimize transfers to human agents"
        },
    }


# ============================================================================
# Function Tools (Optimized)
# ============================================================================

@function_tool
async def get_conversation_quality(ctx: RunContext) -> str:
    """
    Get the current conversation quality metrics.
    
    Use this to check how the conversation is going and monitor customer satisfaction.
    
    Returns:
        JSON string containing conversation quality metrics and status.
    """
    if agent_state.analyzer:
        try:
            summary = agent_state.analyzer.get_summary()
            return json.dumps(summary, indent=2)
        except Exception as e:
            logger.error(f"Error getting conversation quality: {e}")
            return json.dumps({"status": "error", "message": str(e)})
    return json.dumps({"status": "analyzer_not_initialized"})


@function_tool
async def lookup_printer_issue(
    run_ctx: RunContext,
    customer_description: str,
) -> str:
    """
    Look up printer issues and resolutions based on customer's description.
    
    Use this when the customer describes a printer problem to find matching
    knowledge base articles and resolution steps.
    
    Args:
        customer_description: The customer's description of the printer issue
            (e.g., "printer not printing", "paper jam", "ink problem")
    
    Returns:
        JSON string with matching issues, resolutions, and detailed steps
    """
    if not customer_description or len(customer_description.strip()) < 3:
        return json.dumps({
            "status": "invalid_input",
            "message": "Please provide a more detailed description of the printer issue.",
        }, indent=2)
    
    logger.info(f"🔍 Looking up printer issue for: '{customer_description[:100]}'")
    
    try:
        # Search the knowledge base
        matches = agent_state.printer_kb.search_by_caller_description(
            customer_description
        )
        
        if not matches:
            return json.dumps({
                "status": "no_match",
                "message": (
                    "No matching printer issues found. Please ask the customer for "
                    "more details about the problem."
                ),
                "suggestions": [
                    "Ask about specific symptoms (e.g., error messages, lights, sounds)",
                    "Ask about what the customer was trying to print",
                    "Ask if the printer is powered on and connected",
                ],
            }, indent=2)
        
        # Format results (limit to top matches for performance)
        results = []
        for issue in matches[:MAX_ISSUE_MATCHES]:
            try:
                resolution_steps = agent_state.printer_kb.get_resolution_steps(issue)
                result = {
                    "system_alert_type": issue.system_alert_type,
                    "caller_issue_type": issue.caller_issue_type,
                    "resolution": issue.resolution,
                    "impacted_equipment": issue.impacted_equipment,
                    "call_recording_needed": issue.call_recording_needed,
                    "resolution_steps": resolution_steps,
                }
                if issue.special_notes:
                    result["special_notes"] = issue.special_notes
                results.append(result)
            except Exception as e:
                logger.warning(f"Error processing issue {issue.caller_issue_type}: {e}")
                continue
        
        logger.info(f"✅ Found {len(results)} matching printer issue(s)")
        return json.dumps({
            "status": "success",
            "matches": results,
            "count": len(results),
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error looking up printer issue: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to lookup printer issue: {str(e)}",
        }, indent=2)


@function_tool
async def analyze_printer_issue_with_claude(
    run_ctx: RunContext,
    customer_description: str,
    conversation_context: str = "",
) -> str:
    """
    Use Claude AI to analyze a printer issue and provide intelligent recommendations.
    
    This is useful for complex or unusual printer problems that may not be in the
    knowledge base. Falls back to knowledge base lookup if Claude is unavailable.
    
    Args:
        customer_description: The customer's description of the printer problem
        conversation_context: Optional context from the conversation so far
    
    Returns:
        JSON string with Claude's analysis and recommendations
    """
    if not claude_client:
        logger.debug("Claude AI not available, falling back to knowledge base")
        return json.dumps({
            "status": "unavailable",
            "message": (
                "Claude AI is not available. Please use lookup_printer_issue instead."
            ),
        }, indent=2)
    
    if not customer_description or len(customer_description.strip()) < 3:
        return json.dumps({
            "status": "invalid_input",
            "message": "Please provide a more detailed description of the printer issue.",
        }, indent=2)
    
    logger.info(f"🤖 Using Claude to analyze printer issue: '{customer_description[:100]}'")
    
    try:
        prompt = f"""You are a printer support specialist helping a customer with a printer issue.

Customer's description: {customer_description}

{f"Conversation context: {conversation_context}" if conversation_context else ""}

Please analyze this printer issue and provide:
1. Likely cause(s) of the problem
2. Recommended troubleshooting steps
3. Whether this might be a hardware or software issue
4. Any safety considerations

Be concise and practical. Focus on actionable steps the customer can take."""

        message = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": prompt,
            }],
        )
        
        analysis = message.content[0].text
        
        return json.dumps({
            "status": "success",
            "analysis": analysis,
            "model": CLAUDE_MODEL,
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error calling Claude: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to analyze with Claude: {str(e)}",
        }, indent=2)


@function_tool
async def end_conversation(run_ctx: RunContext) -> str:
    """
    End the conversation and close the job.
    
    Use this when the user says goodbye, thanks you, or indicates the conversation
    is complete. This ensures proper cleanup and job closure.
    
    Returns:
        Confirmation message with job ID
    """
    job_context = run_ctx.job_context if hasattr(run_ctx, 'job_context') else None
    
    # Extract job ID safely
    job_id = "unknown"
    try:
        if job_context:
            if hasattr(job_context, 'job_id'):
                job_id = job_context.job_id
            elif hasattr(job_context, 'job') and hasattr(job_context.job, 'id'):
                job_id = job_context.job.id
    except Exception as e:
        logger.debug(f"Could not extract job_id: {e}")
    
    logger.info(f"Ending conversation and closing job_id: {job_id}")
    
    try:
        # Wait for any ongoing playout to complete
        await run_ctx.wait_for_playout()
    except Exception as e:
        logger.debug(f"Error waiting for playout: {e}")
    
    # Disconnect room gracefully
    try:
        if hasattr(run_ctx, 'room') and run_ctx.room:
            await run_ctx.room.disconnect()
        elif job_context and hasattr(job_context, 'room') and job_context.room:
            await job_context.room.disconnect()
    except Exception as e:
        logger.debug(f"Room disconnect error: {e}")
    
    # Disconnect job context
    try:
        if job_context and hasattr(job_context, 'disconnect'):
            await job_context.disconnect()
    except Exception as e:
        logger.debug(f"Job context disconnect error: {e}")
    
    logger.info(f"✅ Job closed successfully. Job ID: {job_id}")
    return f"Conversation ended successfully. Job {job_id} closed."


# ============================================================================
# Quality Change Handler
# ============================================================================

def create_quality_change_handler() -> Callable[[ConversationMetrics], None]:
    """
    Create a quality change handler callback function.
    
    Returns:
        Callback function for handling conversation quality changes
    """
    quality_emoji = {
        ConversationQuality.EXCELLENT: "✅",
        ConversationQuality.GOOD: "👍",
        ConversationQuality.NEUTRAL: "➖",
        ConversationQuality.POOR: "⚠️",
        ConversationQuality.CRITICAL: "🚨",
    }
    
    def on_quality_change(metrics: ConversationMetrics) -> None:
        """Handle conversation quality changes with appropriate logging."""
        emoji = quality_emoji.get(metrics.quality, "➖")
        
        status_msg = (
            f"{emoji} CALL STATUS: {metrics.quality.value.upper()} | "
            f"Sentiment: {metrics.sentiment_score:.2f} | "
            f"Raised Voice: {metrics.raised_voice_detected} | "
            f"Warnings: {metrics.warning_count}"
        )
        
        if metrics.quality in [ConversationQuality.POOR, ConversationQuality.CRITICAL]:
            logger.error(status_msg)
            if metrics.negative_indicators:
                unique_indicators = ', '.join(set(metrics.negative_indicators))
                logger.error(f"   Negative indicators: {unique_indicators}")
            if metrics.quality == ConversationQuality.CRITICAL:
                logger.error(
                    "🚨 CRITICAL: Consider immediate intervention or call escalation!"
                )
        else:
            logger.info(status_msg)
    
    return on_quality_change


# ============================================================================
# Transcript Monitoring (Optimized)
# ============================================================================

def detect_goodbye(transcript: str) -> bool:
    """
    Efficiently detect goodbye keywords in transcript using compiled regex.
    
    Args:
        transcript: The transcript text to check
    
    Returns:
        True if goodbye keywords are detected, False otherwise
    """
    return bool(GOODBYE_PATTERN.search(transcript))


async def process_user_transcript(
    transcript: str,
    analyzer: ConversationAnalyzer,
    ctx: JobContext,
) -> None:
    """
    Process a user transcript with analysis and goodbye detection.
    
    Args:
        transcript: The transcript text to process
        analyzer: The conversation analyzer instance
        ctx: The job context
    """
    if not analyzer or not transcript:
        return
    
    transcript_text = transcript.strip()
    
    # Quick validation
    if len(transcript_text) <= TRANSCRIPT_MIN_LENGTH:
        return
    
    # Check if already analyzed (using set for O(1) lookup)
    if transcript_text in agent_state.analyzed_transcripts:
        return
    
    # Add to analyzed set
    agent_state.add_analyzed_transcript(transcript_text)
    
    try:
        logger.info(f"📝 Captured user transcript: '{transcript_text[:100]}'")
        
        # Analyze transcript
        await analyzer.analyze_text(transcript_text, is_agent=False)
        
        # Log metrics (only if significant)
        metrics = analyzer.get_metrics()
        if metrics.warning_count > 0 or abs(metrics.sentiment_score) > 0.1:
            logger.info(
                f"📊 Conversation Status Update | "
                f"Quality: {metrics.quality.value.upper()} | "
                f"Sentiment: {metrics.sentiment_score:.2f} | "
                f"Raised Voice: {metrics.raised_voice_detected} | "
                f"Warnings: {metrics.warning_count}"
            )
        
        # Check for goodbye
        if detect_goodbye(transcript_text):
            logger.info(
                f"👋 Goodbye detected in transcript: '{transcript_text[:100]}' - "
                "Job will be closed after response"
            )
            try:
                job_id = (
                    ctx.job_id if hasattr(ctx, 'job_id')
                    else getattr(ctx.job, 'id', 'unknown') if hasattr(ctx, 'job') else 'unknown'
                )
                logger.info(f"Preparing to close job_id: {job_id}")
            except Exception as e:
                logger.debug(f"Error getting job_id: {e}")
                
    except Exception as e:
        logger.error(f"Error processing user transcript: {e}")


async def monitor_user_transcriptions(
    session: AgentSession,
    analyzer: ConversationAnalyzer,
    ctx: JobContext,
) -> None:
    """
    Optimized monitoring loop for user transcriptions.
    
    Args:
        session: The agent session
        analyzer: The conversation analyzer
        ctx: The job context
    """
    analyzed_texts: Set[str] = set()
    last_message_count = 0
    status_update_counter = 0
    last_interceptor_count = 0
    
    while True:
        try:
            await asyncio.sleep(MONITORING_INTERVAL)
            
            if not analyzer:
                continue
            
            # Process new transcripts from interceptor
            current_interceptor_count = len(transcript_interceptor.transcripts)
            if current_interceptor_count > last_interceptor_count:
                for transcript in transcript_interceptor.transcripts[last_interceptor_count:]:
                    if transcript and transcript not in analyzed_texts:
                        await process_user_transcript(transcript, analyzer, ctx)
                        analyzed_texts.add(transcript)
                last_interceptor_count = current_interceptor_count
            
            # Process messages from chat context
            try:
                if hasattr(session, 'chat_ctx') and session.chat_ctx:
                    messages = getattr(session.chat_ctx, 'messages', [])
                    current_message_count = len(messages)
                    
                    if current_message_count > last_message_count:
                        for msg in messages[last_message_count:]:
                            if hasattr(msg, 'role') and msg.role == 'user':
                                content = (
                                    getattr(msg, 'content', '') or
                                    getattr(msg, 'text', '') or
                                    str(msg)
                                )
                                if (content and content not in analyzed_texts and
                                    len(content.strip()) > TRANSCRIPT_MIN_LENGTH):
                                    await process_user_transcript(content, analyzer, ctx)
                                    analyzed_texts.add(content)
                        
                        last_message_count = current_message_count
                        
                        # Cleanup analyzed texts cache
                        if len(analyzed_texts) > TRANSCRIPT_CACHE_SIZE:
                            analyzed_texts.clear()
            except Exception as e:
                logger.debug(f"Error processing chat context messages: {e}")
            
            # Process user messages directly
            try:
                if hasattr(session, 'user') and session.user:
                    if hasattr(session.user, 'messages'):
                        for msg in session.user.messages:
                            content = (
                                getattr(msg, 'content', '') or
                                getattr(msg, 'text', '') or
                                str(msg)
                            )
                            if (content and content not in analyzed_texts and
                                len(content.strip()) > TRANSCRIPT_MIN_LENGTH):
                                await process_user_transcript(content, analyzer, ctx)
                                analyzed_texts.add(content)
            except Exception as e:
                logger.debug(f"Error processing user messages: {e}")
            
            # Periodic status update
            status_update_counter += 1
            if status_update_counter >= STATUS_UPDATE_INTERVAL:
                status_update_counter = 0
                try:
                    metrics = analyzer.get_metrics()
                    if (metrics.warning_count > 0 or
                        metrics.sentiment_score != 0.0 or
                        len(analyzer.conversation_history) > 0):
                        on_quality_change = create_quality_change_handler()
                        on_quality_change(metrics)
                except Exception as e:
                    logger.debug(f"Error in status update: {e}")
                    
        except Exception as e:
            logger.debug(f"Monitoring loop error: {e}")


def setup_transcript_hooks(
    session: AgentSession,
    ctx: JobContext,
) -> None:
    """
    Set up transcript hooks for various message sources.
    
    Args:
        session: The agent session
        ctx: The job context
    """
    async def on_user_transcript_wrapper(transcript: str) -> None:
        """Wrapper for processing user transcripts."""
        if agent_state.analyzer:
            await process_user_transcript(transcript, agent_state.analyzer, ctx)
    
    # Hook into session user messages
    try:
        if hasattr(session, 'on_user_message'):
            original_handler = session.on_user_message
            
            async def wrapped_handler(message: Any) -> None:
                if original_handler:
                    await original_handler(message)
                if hasattr(message, 'content'):
                    await on_user_transcript_wrapper(message.content)
            
            session.on_user_message = wrapped_handler
    except Exception as e:
        logger.debug(f"Error setting up session user message hook: {e}")
    
    # Hook into room data packets
    try:
        if hasattr(ctx.room, 'on'):
            def on_data_received(data: rtc.DataPacket) -> None:
                if data.data and isinstance(data.data, (str, bytes)):
                    try:
                        text = (
                            data.data.decode() if isinstance(data.data, bytes)
                            else data.data
                        )
                        if text and len(text.strip()) > TRANSCRIPT_MIN_LENGTH:
                            asyncio.create_task(on_user_transcript_wrapper(text))
                    except Exception as e:
                        logger.debug(f"Error processing data packet: {e}")
            
            ctx.room.on("data_received", on_data_received)
    except Exception as e:
        logger.debug(f"Error setting up room data hook: {e}")


# ============================================================================
# Main Entrypoint
# ============================================================================

async def entrypoint(ctx: JobContext) -> None:
    """
    Main entrypoint for the telephony agent.
    
    Initializes the agent, sets up conversation analysis, and starts the session.
    
    Args:
        ctx: The job context from LiveKit
    """
    await ctx.connect()
    
    # Extract phone number from participant if available
    try:
        participant = await ctx.wait_for_participant()
        if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
            phone_number = participant.attributes.get('sip.phoneNumber', DEFAULT_PHONE_NUMBER)
            agent_state.phone_number = phone_number
            logger.info(f"📞 Connected to phone number: {phone_number}")
    except Exception as e:
        logger.warning(f"Could not extract participant phone number: {e}")
    
    # Build agent configuration
    script_config = build_agent_config()
    
    # Create function tools
    tools = [
        get_conversation_quality,
        lookup_printer_issue,
        analyze_printer_issue_with_claude,
        end_conversation,
    ]
    
    # Create agent
    agent = Agent(
        instructions=json.dumps(script_config, indent=2),
        tools=tools,
    )
    
    # Configure MCP servers (optional)
    mcp_servers: List[Any] = []
    try:
        mcp_servers = [mcp.MCPServerHTTP(MCP_SERVER_URL)]
        logger.info(f"✅ MCP server configured: {MCP_SERVER_URL}")
    except Exception as e:
        logger.debug(f"MCP server not configured: {e}")
    
    # Create session configuration
    session_config = SessionConfig()
    
    # Create agent session
    session = AgentSession(
        mcp_servers=mcp_servers,
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=openai.LLM(model=session_config.llm_model),
        tts=cartesia.TTS(
            model=session_config.tts_model,
            language=session_config.tts_language,
            voice=session_config.tts_voice,
        ),
    )
    
    # Create quality change handler
    on_quality_change = create_quality_change_handler()
    
    # Start session
    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
    )
    
    # Initialize conversation analyzer
    agent_state.analyzer = ConversationAnalyzer(
        session=session,
        room=ctx.room,
        on_quality_change=on_quality_change,
        audio_threshold=session_config.audio_threshold,
    )
    
    # Set up transcript hooks
    setup_transcript_hooks(session, ctx)
    
    # Start monitoring task
    asyncio.create_task(monitor_user_transcriptions(session, agent_state.analyzer, ctx))
    
    # Generate initial greeting following the technical support call flow
    await session.generate_reply(instructions="""
        Follow the technical support call flow script:
        
        STEP 1 - GREETING & ISSUE IDENTIFICATION:
        Say: "Thank you for calling Catalina Marketing support. My name is Kim. How can I help you today?"
        Wait for customer response.
        If they mention a printer issue, say: "I understand you're having an issue with your printer. I'll be happy to help you with that. Before we begin, let me verify some information."
        
        STEP 2 - CUSTOMER VERIFICATION:
        Ask for phone number: "Could you please confirm your phone number for me?"
        Wait for response, then repeat it back: "Thank you. I have [repeat phone number]. Is that correct?"
        Wait for confirmation.
        Then ask: "Great. And can you confirm your address?"
        Wait for response, then repeat it back: "Perfect. I have [repeat address]. Is that correct?"
        Wait for confirmation.
        
        STEP 3 - DEVICE VERIFICATION:
        Ask: "Now, can you please provide me with the serial number of your printer? You can usually find this on the back or bottom of the device."
        Wait for response, then repeat it back: "Thank you. That's serial number [repeat serial number]. Is that correct?"
        Wait for confirmation.
        
        STEP 4 - ISSUE DIAGNOSIS:
        Ask: "Now, can you tell me what issue you're experiencing with your printer?"
        Listen for: blinking lights, paper jams, not printing, error messages, connection issues.
        Then say: "I understand. You mentioned [summarize issue]. Can you tell me when this problem started?"
        Wait for response.
        Then ask: "Thank you for that information. And what color is the light that's blinking on your printer?"
        
        After gathering this information, use the lookup_printer_issue function to find the appropriate troubleshooting steps.
    """)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="telephony-agent",
    ))
