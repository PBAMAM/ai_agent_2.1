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
import time
import numpy as np
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
import numpy as np
import sys
import subprocess
import io

from conversation_analyzer import (
    ConversationAnalyzer,
    ConversationMetrics,
    ConversationQuality,
)
from printer_knowledge_base import PrinterKnowledgeBase, PrinterIssue
from system_tools import SystemTools
from personality import AdaptivePersonality

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
MONITORING_INTERVAL = 0.3  # seconds - faster for real-time processing
STATUS_UPDATE_INTERVAL = 10  # iterations
AUDIO_THRESHOLD = 0.7
MAX_ISSUE_MATCHES = 3
BACKCHANNEL_THRESHOLD = 1.2  # seconds of user speech before backchanneling (more frequent)
PROACTIVE_SEARCH_THRESHOLD = 1.5  # seconds before starting proactive search

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
    llm_model: str = "gpt-5-mini"
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
        self.system_tools: SystemTools = SystemTools()
        self.personality: AdaptivePersonality = AdaptivePersonality()
        self.current_session: Optional[AgentSession] = None
        self.user_speaking_start_time: Optional[float] = None
        self.last_backchannel_time: Optional[float] = None
        self.pending_searches: Dict[str, asyncio.Task] = {}  # Track proactive searches
        self.interim_transcripts: List[str] = []  # Store interim transcripts
        self.background_audio_task: Optional[asyncio.Task] = None  # Background office sounds
        self.agent_speaking: bool = False  # Track if agent is currently speaking
        self.background_audio_source: Optional[rtc.AudioSource] = None  # Audio source for background sounds
    
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
            "greeting_style": (
                "Thank you for calling Catalina Marketing support. How can I help you today? "
                "Say this greeting only once at the very start of the call. "
                "Do NOT repeat 'Thank you for calling' multiple times or echo it back to the caller."
            ),
            
            "introduce_yourself_with_name": (
                "You may briefly introduce yourself once at the start, like "
                "\"I'm Kim from support\", but do not keep repeating your name "
                "throughout the call."
            ),
            
            "call_flow": {
                "step_1_greeting": (
                    "After greeting, ask an open, friendly question like "
                    "'What can I help you with today?' or 'What seems to be going on?'. "
                    "Let the caller talk. Do NOT assume they have a printer issue until they clearly mention "
                    "a printer or printing problem. "
                    "ONLY AFTER they mention a printer issue, you may say something natural like: "
                    "'Okay, no problem at all, I can help you with that.' "
                    "Then smoothly transition into any information you actually need, without sounding scripted."
                ),
                "step_2_customer_verification": (
                    "If needed, ask for phone number and address in a natural way, one at a time. "
                    "Avoid sounding like a form. If the caller seems impatient or the info is already known, "
                    "you may skip repeating every detail back word-for-word."
                ),
                "step_3_device_verification": "Ask for serial number: 'Now, can you please provide me with the serial number of your printer? You can usually find this on the back or bottom of the device.' After they provide it, repeat it back: 'Thank you. That's serial number [repeat serial number]. Is that correct?' Wait for confirmation.",
                "step_4_issue_diagnosis": (
                    "Ask about the issue in a conversational way: 'Can you tell me what's going on with it?'. "
                    "Listen first, then ask only the follow‑up questions you actually need. "
                    "Do NOT fire off a long list of back‑to‑back questions. "
                    "Ask one question, listen, respond, then move to the next."
                ),
                "step_5_troubleshooting": "Use lookup_printer_issue to find the appropriate troubleshooting steps. Walk through steps ONE at a time, waiting for confirmation after each step.",
                "step_6_verification": "After troubleshooting, verify: 'Excellent! I'm glad we were able to resolve that for you. Let's do a quick test to make sure everything is working properly. Can you try printing a test page for me?' Wait for customer to print. Ask: 'Great! Did the test page print successfully?' If successful: 'Perfect! Your printer is now back online and working properly.' If not: 'I see. Let's try [alternative troubleshooting step] or I can escalate this to our technical team for further assistance.'",
                "step_7_additional_issues": "Ask: 'Is there anything else I can help you with today?' If they mention another issue, help with that. If they mention billing: 'I understand you're having a billing issue. Let me look into that for you. Can you tell me more about the billing concern?'",
                "step_8_closing": "If no additional issues: 'I'm glad I could help you today. Just to recap, we've successfully resolved your printer issue by [summarize resolution]. Your printer should now be working properly.' Then: 'Before we end this call, I want to remind you that you can reach our support team anytime if you need assistance. Is there anything else I can clarify for you?' After response: 'Thank you for calling Catalina Marketing support. Have a great day!'"
            },

            "printer_support_focus": (
                "You are a printer support specialist for Catalina Marketing printers (CMC6, CMC7, CMC8, CMC9). "
                "Your mission is to help store staff troubleshoot and resolve printer issues remotely with patience, "
                "clarity, and step-by-step instructions. "
                "However, NEVER assume the caller's problem is about a printer until they clearly say so. "
                "Start by asking what they need help with, listen, and only talk about printers after they mention it."
            ),

            "printer_issue_handling": {
            "listen_carefully": "Ask deeper questions about the issue: Ask which line the printer is on (example: Line 1, Line 5). Ask if there are blinking lights, noises, errors, paper jams, out of paper, ink issues, blank/faded prints, or communication errors.",
            "use_knowledge_base": "ALWAYS use lookup_printer_issue before giving any troubleshooting instruction.",
            "use_system_tools": "You have access to system integration tools: check_printer_status (to verify printer state), send_test_print (to test printer), perform_ink_cleaning (for print quality issues), get_store_information (to get store details), and update_service_ticket (to document the call). Use these tools when appropriate.",
            "follow_steps": "Follow troubleshooting steps exactly as written. Give ONE step at a time, and wait for POC confirmation before moving on.",
            "provide_resolution": "Guide the POC step-by-step. Use simple language and be patient. Adapt your communication style based on the customer's cooperation level.",
            "verify_resolution": "After troubleshooting, verify the printer status using check_printer_status, confirm prints are working, or assist with print quality checks.",
            "call_recording": "Remember that printer support calls may be recorded for quality and training.",
            "test_prints": "Do NOT send test prints unless the POC specifically asks for them. Use send_test_print tool only when requested or after resolving an issue.",
            "cleaning_cycle": "If print quality issues occur or blinking light issue, you can use perform_ink_cleaning tool for remote cleaning, or guide them manually: 'Okay, based on what you've described, it sounds like your printer may need a cleaning cycle. I'm going to walk you through this process. It will take about one minute. Are you ready?' Wait for confirmation. Then guide them: 'First, locate the [specific button] on your printer. Can you see it?' Wait for confirmation. 'Now, press and hold that button for about 3 seconds until the light changes. Let me know when you've done that.' Wait for customer action. 'Perfect. You're doing great. Now the printer should begin its cleaning cycle. This will take about a minute. The light may blink during this process - that's normal. Let's wait for it to complete.' While waiting: 'While we're waiting, I want to let you know that this cleaning cycle helps maintain your printer's print quality and can resolve many common issues.' After cleaning cycle: 'Okay, the cleaning cycle should be complete now. Can you check the printer? The light should now be solid green and no longer blinking. What do you see?'",
            "dispatch_escalation": "If remote troubleshooting fails, offer escalation. Ask: 'I can escalate this ticket and send a technician to your location if you'd like. Would you like me to arrange a tech visit?' Use update_service_ticket to document escalation.",
            "natural_language_patterns": {
                "opening": [
                    "Hi there! This is {agent_name} from Catalina support. I'm calling about the printer on Lane {lane} - I can see it's showing {issue}. Do you have a quick minute to help me check on it?",
                    "Good {time_of_day}! My name is {agent_name} with Catalina. I'm reaching out because we've detected {issue} on your Lane {lane} printer. Would you be able to take a look at it with me?"
                ],
                "acknowledging_busy": [
                    "I totally understand you're busy right now. This should only take about {estimated_time} minutes, and then you'll be all set.",
                    "I know you've got a lot going on. Let's get this sorted quickly so it doesn't hold you up."
                ],
                "providing_instructions": [
                    "Okay, here's what I need you to do: {instruction}. Just take your time, and let me know when you're ready for the next step.",
                    "Alright, so if you could {instruction} for me. And don't worry, I'll walk you through everything step by step."
                ],
                "checking_status": [
                    "Let me just check something on my end real quick... {thinking_pause} ... Okay, I can see that {finding}.",
                    "Give me just a second while I pull that up... {system_query} ... Alright, so what I'm seeing is {finding}."
                ],
                "celebrating_success": [
                    "Perfect! That did the trick. The printer is back online and looking good.",
                    "Excellent! We're all set. The issue is resolved and everything should be working normally now."
                ],
                "expressing_empathy": [
                    "I know dealing with printer issues can be frustrating, especially when you're in the middle of a rush.",
                    "I really appreciate your patience with this. I know it's not convenient timing."
                ],
                "handling_complications": [
                    "Okay, so that didn't quite do what we were hoping for. Let's try a different approach.",
                    "Hmm, that's interesting. Let me check one more thing on my end to see what else might be going on."
                ]
            }
            },

            "communication_with_poc": {
            "be_clear_and_patient": (
                "Use friendly, simple language. Speak slowly and clearly. "
                "Adapt your pace and detail level based on the customer's cooperation score - "
                "if they seem frustrated or confused, slow down and provide more detail."
            ),
            "natural_conversation": (
                "IMPORTANT: This is a natural conversation, not a scripted interaction. "
                "Be direct and to the point. Focus on the problem and the next concrete step. "
                "Use brief acknowledgments like 'Okay', 'Got it', 'Alright' while they're speaking "
                "to show you're listening, but only occasionally. "
                "Avoid overusing phrases like 'no problem', 'thank you', or 'thanks' – use them only when "
                "they really fit, not in every sentence. "
                "Do NOT repeat the same acknowledgment over and over or interrupt too often."
            ),
            "proactive_behavior": "IMPORTANT: Don't wait for the customer to finish speaking before you start looking for solutions. As soon as you hear keywords like 'paper', 'ink', 'not printing', 'error', 'blinking light', etc., immediately start searching for solutions using lookup_printer_issue. While searching, ALWAYS say something like 'Let me check that for you' or 'I'm looking into that' - never stay silent while searching. Be proactive and start working on the problem while they're still explaining.",
            "interruptions": "You can be interrupted by the customer, and you can interrupt them with brief acknowledgments. This is natural conversation flow. If you're interrupted, gracefully stop and listen. If you need to interrupt, use brief phrases like 'I understand', 'Okay', 'Got it' to show you're listening.",
            "confirm_understanding": "Ask 'Do you see that?', 'Can you confirm for me?', 'Let me know when you're ready for the next step.'",
            "provide_encouragement": "Say things like 'You're doing great', 'Nice job', 'Perfect, thank you', 'You're doing great, we're almost there'. Adjust encouragement frequency based on cooperation level.",
            "adaptive_personality": "Your personality adapts based on customer cooperation: For cooperative customers (score >70), be efficient and appreciative. For reluctant customers (score <40), be very patient, empathetic, and provide more encouragement. For balanced customers (40-70), use standard friendly professional tone.",
            "handle_unwilling_poc": "If the POC refuses or cannot assist, follow the standard Unwilling POC process. Increase empathy and patience.",
            "store_specific_handling": "Ask early: 'Are you calling from Walgreens, Kroger, Meijer, HEB, or another store?' Some retailers have special procedures. Use get_store_information to retrieve store details if needed.",
            "empathy_statements": [
                "I get that this is annoying.",
                "I know this isn't ideal.",
                "I hear you.",
                "Let's sort this out."
            ],
            "reassurance_statements": [
                "We'll get this figured out.",
                "Let me walk you through the next step.",
                "Let's try something simple first."
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
            "tone": (
                "sound like a real human support agent, not an AI. "
                "Be friendly and professional, patient and reassuring, clear and articulate. "
                "Use a warm, natural tone with subtle variation and short pauses. "
                "It's okay to have small human imperfections, like a brief hesitation or a quick self‑correction "
                "('sorry, let me say that more clearly'), but do NOT overdo it."
            ),
            "pace": (
                "Speak slowly and clearly, at a relaxed pace. "
                "Keep each response very short: usually 1–2 short sentences. "
                "Avoid long monologues. "
                "Pause after questions to allow customer response (wait 3-5 seconds). "
                "Slow down for technical steps. "
                "SLOW and methodical - present ONE step, WAIT for confirmation, then proceed. "
                "Give the customer time to physically complete each action. Never rush or give "
                "multiple steps at once."
            ),
            "language": (
                "Use very clear, simple, human language. "
                "Use contractions and natural phrasing ('I'm', 'we'll', 'let's', 'you're'). "
                "Prefer short sentences with one idea at a time. "
                "Avoid sounding like you're reading from a script. Avoid technical jargon unless necessary, and "
                "explain technical terms when used."
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
            "⚠️ CRITICAL: Use the 8-step call flow as a flexible guideline, not a rigid script. "
            "Adapt the order and which steps you use based on what the caller has already told you.",
            "⚠️ CRITICAL: Give ONE troubleshooting step at a time, then STOP and WAIT for confirmation.",
            "⚠️ CRITICAL: Do NOT list multiple steps in a row - present step 1, wait for completion, then present step 2.",
            "After each important step, check in briefly (for example 'Did that help?' or 'How did that go?'), "
            "but do NOT repeat the same question more than once. If you need to ask again, rephrase it naturally "
            "or move on based on what the caller has already said.",
            "For critical details like phone numbers or serial numbers, confirm them, but keep it short and natural. "
            "Don't repeat long strings of numbers more than necessary.",
            "Allow 3-5 seconds after each question for customer response and avoid stacking questions together. "
            "Do NOT ask a long series of questions back-to-back; ask one, listen, respond, then decide if you "
            "really need another.",
            "Be direct and efficient. Get to the point quickly instead of adding small talk or repeated 'thank you' / 'no problem' phrases.",
            "Always be respectful of the customer's time and situation - they may be busy with customers.",
            "If the customer seems busy or distracted, offer to call back later.",
            "Never rush the customer through troubleshooting steps - accuracy is more important than speed.",
            "Be patient and methodical - wait for the customer to physically complete each action.",
            "Be honest about what you can and cannot do remotely.",
            "Use natural conversation flow - don't sound like you're reading from a script.",
            "Speak naturally and conversationally - don't mention that you're following a script or reading instructions.",
            "IMPORTANT: When the user says goodbye, thanks you, or indicates the conversation is complete, "
            "you MUST call the end_conversation function to properly close the job",
            "For outbound calls (system alerts), test coupons are only sent if the customer requests them",
            "Always verify printer status and print quality before closing a ticket",
            "Follow store-specific handling procedures when applicable (Walgreens, Kroger, Meijer, HEB, etc.)",
            "If customer interrupts, acknowledge and adjust flow accordingly",
            "If customer answer is unclear, politely ask them to repeat",
            "Document all actions taken during the call for future reference",
            "Offer to send summary email with troubleshooting steps if helpful",
            "Do NOT say phrases like 'the conversation has ended' or 'I am ending this conversation' to the caller. "
            "Just close naturally with a normal polite goodbye.",
            "Do NOT repeat the opening line 'Thank you for calling Catalina Marketing support' more than once. "
            "If the caller says 'hello' or greets you, respond naturally without saying the full thank-you line again.",
            "Never say that you are an AI, a bot, a language model, or mention OpenAI, models, tools, or prompts. "
            "Always speak as a human support agent on the phone.",
            "If the caller asks if you are an AI, a bot, or a robot, ALWAYS answer 'No' and continue the conversation "
            "naturally as a human support agent.",
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
    
    IMPORTANT: While searching, say something like "Let me check that for you" or 
    "I'm looking into that" to acknowledge you're working on it. Don't stay silent.
    
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
    
    # Speak while searching to make it natural
    if agent_state.current_session:
        try:
            search_phrases = [
                "Let me check that for you",
                "I'm looking into that right now",
                "Let me see what I can find about that",
                "I'm checking on that for you"
            ]
            import random
            search_phrase = random.choice(search_phrases)
            logger.info(f"💬 Speaking while searching: '{search_phrase}'")
            asyncio.create_task(
                agent_state.current_session.generate_reply(
                    instructions=f"Say ONLY this exact phrase, nothing else: '{search_phrase}'. Keep it brief."
                )
            )
        except Exception as e:
            logger.debug(f"Error speaking during lookup: {e}")
    
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
async def check_printer_status(
    run_ctx: RunContext,
    chain: int,
    store: int,
    lane: int,
) -> str:
    """
    Check the current status of a printer via system connection.
    
    Use this to verify printer status after troubleshooting steps or to diagnose issues.
    
    Args:
        chain: Chain ID (integer)
        store: Store number (integer)
        lane: Lane number where the printer is located (integer)
    
    Returns:
        JSON string with printer status information
    """
    logger.info(f"🔍 Checking printer status: Chain {chain}, Store {store}, Lane {lane}")
    
    try:
        result = await agent_state.system_tools.check_printer_status(
            chain=chain,
            store=store,
            lane=lane
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error checking printer status: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to check printer status. Please verify store and lane information."
        }, indent=2)


@function_tool
async def send_test_print(
    run_ctx: RunContext,
    chain: int,
    store: int,
    lane: int,
) -> str:
    """
    Send a test coupon to verify printer is working.
    
    Use this after troubleshooting to verify the printer is functioning correctly.
    Only use this if the customer requests a test print or after resolving an issue.
    
    Args:
        chain: Chain ID (integer)
        store: Store number (integer)
        lane: Lane number where the printer is located (integer)
    
    Returns:
        JSON string with test print result
    """
    logger.info(f"🖨️ Sending test print: Chain {chain}, Store {store}, Lane {lane}")
    
    try:
        result = await agent_state.system_tools.send_test_print(
            chain=chain,
            store=store,
            lane=lane
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error sending test print: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to send test print. Please verify printer is online."
        }, indent=2)


@function_tool
async def perform_ink_cleaning(
    run_ctx: RunContext,
    chain: int,
    store: int,
    lane: int,
) -> str:
    """
    Perform a remote ink cleaning cycle on the printer.
    
    Use this when print quality issues are reported or when a cleaning cycle is needed.
    The cleaning cycle takes approximately 60 seconds.
    
    Args:
        chain: Chain ID (integer)
        store: Store number (integer)
        lane: Lane number where the printer is located (integer)
    
    Returns:
        JSON string with cleaning cycle status
    """
    logger.info(f"🧹 Performing ink cleaning: Chain {chain}, Store {store}, Lane {lane}")
    
    try:
        result = await agent_state.system_tools.perform_ink_cleaning(
            chain=chain,
            store=store,
            lane=lane
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error performing ink cleaning: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to initiate ink cleaning cycle."
        }, indent=2)


@function_tool
async def update_service_ticket(
    run_ctx: RunContext,
    ticket_id: str,
    status: str,
    resolution_notes: str,
) -> str:
    """
    Update a ServiceNow ticket with status and resolution notes.
    
    Use this to document the call, resolution steps, and final status.
    
    Args:
        ticket_id: ServiceNow ticket ID (string)
        status: Ticket status - "resolved", "escalated", or "in_progress" (string)
        resolution_notes: Detailed notes about the issue and resolution (string)
    
    Returns:
        JSON string with update result
    """
    logger.info(f"📝 Updating ticket {ticket_id} with status: {status}")
    
    try:
        result = await agent_state.system_tools.update_ticket(
            ticket_id=ticket_id,
            status=status,
            resolution_notes=resolution_notes
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error updating ticket: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to update ticket. Please document manually."
        }, indent=2)


@function_tool
async def get_store_information(
    run_ctx: RunContext,
    chain: int,
    store: int,
) -> str:
    """
    Get store information from StoreMaster database.
    
    Use this to retrieve store details, contact information, and configuration.
    
    Args:
        chain: Chain ID (integer)
        store: Store number (integer)
    
    Returns:
        JSON string with store information
    """
    logger.info(f"🏪 Getting store information: Chain {chain}, Store {store}")
    
    try:
        result = await agent_state.system_tools.get_store_info(
            chain=chain,
            store=store
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting store info: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve store information."
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
    
    # Cleanup system connections
    try:
        await agent_state.system_tools.close()
        logger.info("System connections closed")
    except Exception as e:
        logger.debug(f"Error closing system connections: {e}")
    
    # Reset personality state
    try:
        agent_state.personality.reset()
    except Exception as e:
        logger.debug(f"Error resetting personality: {e}")
    
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


# Backchanneling phrases for natural conversation
BACKCHANNEL_PHRASES = [
    "Uh-huh",
    "Yes",
    "Go on",
    "I see",
    "Okay",
    "Right",
    "Mmm-hmm",
    "Got it",
    "Sure",
    "Alright",
    "I understand",
    "I hear you",
    "Yeah",
    "Okay, I'm listening",
    "Keep going"
]

def get_backchannel_phrase() -> str:
    """Get a random backchannel phrase for natural conversation."""
    import random
    return random.choice(BACKCHANNEL_PHRASES)


# ============================================================================
# Test MP3 Loading (Standalone)
# ============================================================================


# ============================================================================
# Background Office Sounds Generator
# ============================================================================

class OfficeSoundGenerator:
    """
    Generates synthetic office ambient sounds (keyboard, phone, hum) for background audio.
    
    This avoids heavy MP3 processing and guarantees audible background noise.
    """

    def __init__(self, sample_rate: int = 24000, mp3_file: str = "Office Sounds 30 minutes.mp3"):
        self.sample_rate = sample_rate
        self.frame_duration = 0.02  # 20ms frames
        self.samples_per_frame = int(sample_rate * self.frame_duration)
        logger.info("✅ Office sound generator initialized (synthetic mode)")

    def _generate_office_frame(self) -> np.ndarray:
        """
        Generate a single 20ms frame of office-like sound:
        - Base ambient noise
        - Occasional keyboard clicks
        - Rare short phone-like tone
        - Low-frequency office hum
        """
        # Time axis for this frame
        t = np.linspace(0, self.frame_duration, self.samples_per_frame, endpoint=False)

        # Base ambient noise (low volume)
        ambient = 0.015 * np.random.randn(self.samples_per_frame).astype(np.float32)

        # Low-frequency hum (like HVAC/office electronics)
        hum = 0.01 * np.sin(2 * np.pi * 60 * t)  # 60 Hz
        ambient += hum.astype(np.float32)

        # Occasional keyboard click (short high-frequency burst)
        if np.random.rand() < 0.25:  # 25% chance per frame
            click_len = int(self.samples_per_frame * 0.4)  # 40% of frame
            click_t = np.linspace(0, click_len / self.sample_rate, click_len, endpoint=False)
            click = (
                0.08 * np.sin(2 * np.pi * 1200 * click_t) * np.exp(-click_t * 40)
            ).astype(np.float32)
            ambient[:click_len] += click

        # Rare phone "ping" (very short dual-tone)
        if np.random.rand() < 0.03:  # 3% chance per frame
            ring_len = int(self.samples_per_frame * 0.8)
            ring_t = np.linspace(0, ring_len / self.sample_rate, ring_len, endpoint=False)
            ring = (
                0.04 * (np.sin(2 * np.pi * 440 * ring_t) + np.sin(2 * np.pi * 480 * ring_t))
            ).astype(np.float32)
            envelope = np.linspace(0.0, 1.0, ring_len // 4, endpoint=False)
            envelope = np.concatenate(
                [
                    envelope,
                    np.ones(ring_len - 2 * len(envelope), dtype=np.float32),
                    envelope[::-1],
                ]
            )
            ring *= envelope[:ring_len]
            ambient[:ring_len] += ring

        # Clamp to safe range
        ambient = np.clip(ambient, -0.3, 0.3)
        return ambient.astype(np.float32)

    def generate_frame(self, include_sound: bool = True) -> rtc.AudioFrame:
        """Generate a single stereo audio frame with office background sound."""
        if include_sound:
            audio_data = self._generate_office_frame()
        else:
            audio_data = np.zeros(self.samples_per_frame, dtype=np.float32)

        # Create stereo (duplicate mono to stereo)
        stereo_data = np.stack([audio_data, audio_data])

        frame = rtc.AudioFrame(
            data=stereo_data.tobytes(),
            sample_rate=self.sample_rate,
            num_channels=2,
            samples_per_channel=self.samples_per_frame,
        )

        return frame


async def play_background_office_sounds(
    room: rtc.Room,
    sound_generator: OfficeSoundGenerator,
) -> None:
    """
    Play background office sounds while agent is speaking.
    
    Args:
        room: The LiveKit room
        sound_generator: The office sound generator
    """
    publication = None
    try:
        # Create audio source
        source = rtc.AudioSource(sound_generator.sample_rate, 2)  # 2 channels (stereo)
        track = rtc.LocalAudioTrack.create_audio_track("office-ambient", source)
        
        # Publish track to room
        options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        publication = await room.local_participant.publish_track(track, options)
        
        agent_state.background_audio_source = source
        
        logger.info("🔊 Background office sounds started - continuous audio stream active")
        
        # Generate continuous background audio frames for the entire call
        frame_interval = sound_generator.frame_duration
        last_sound_time = 0
        frame_count = 0

        logger.info("🎵 Starting continuous background office audio")

        while True:
            await asyncio.sleep(frame_interval)
            frame_count += 1

            try:
                current_time = time.time()
                import random

                # Always play sounds, but more frequently when agent is speaking
                if agent_state.agent_speaking:
                    # Agent speaking - play sounds more frequently (every 0.2-0.8 seconds)
                    should_play_sound = (current_time - last_sound_time >= random.uniform(0.2, 0.8))
                else:
                    # Agent not speaking - play sounds less frequently (every 1-3 seconds)
                    should_play_sound = (current_time - last_sound_time >= random.uniform(1.0, 3.0))

                # Generate frame with sound
                frame = sound_generator.generate_frame(include_sound=should_play_sound)
                # Use await to ensure frame is captured properly
                await source.capture_frame(frame)

                if should_play_sound:
                    last_sound_time = current_time
                    if frame_count % 50 == 0:  # Log every 50 frames (1 second)
                        logger.info(f"🔊 Office sound played (frame {frame_count}, speaking={agent_state.agent_speaking})")

            except Exception as e:
                logger.warning(f"Error generating background sound: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"Error in background office sounds: {e}", exc_info=True)
    finally:
        try:
            if publication:
                await room.local_participant.unpublish_track(publication)
                logger.info("🔇 Background office sounds stopped")
        except Exception as e:
            logger.debug(f"Error unpublishing background audio: {e}")


def setup_agent_speaking_detection(session: AgentSession, room: rtc.Room) -> None:
    """Set up detection for when agent starts/stops speaking."""
    try:
        # Hook into session events if available
        if hasattr(session, 'on'):
            def on_agent_speech_start():
                agent_state.agent_speaking = True
                logger.info("🎤 Agent speech detected via event - background sounds ON")

            def on_agent_speech_end():
                agent_state.agent_speaking = False
                logger.info("🔇 Agent speech ended via event - background sounds OFF")

            try:
                session.on("agent_speech_start", on_agent_speech_start)
                session.on("agent_speech_end", on_agent_speech_end)
                logger.info("✅ Session event handlers registered")
            except Exception as e:
                logger.debug(f"Session events not available: {e}")

        # Hook into room audio tracks to detect agent speaking
        try:
            def on_track_published(publication: rtc.LocalTrackPublication, participant: rtc.LocalParticipant):
                if publication.kind == rtc.TrackKind.KIND_AUDIO:
                    logger.info(f"🎵 Audio track published: {publication.name}")
                    if hasattr(publication, 'track'):
                        track = publication.track
                        if track:
                            logger.info(f"✅ Audio track available: {track.kind}")

            def on_track_subscribed(track: rtc.RemoteAudioTrack, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
                logger.info(f"🎧 Remote audio track subscribed: {publication.name}")
                # This is the agent's own audio track coming back
                if hasattr(track, 'on'):
                    def on_frame_received(frame):
                        if hasattr(frame, 'samples_per_channel') and frame.samples_per_channel > 0:
                            # Agent is producing audio - likely speaking
                            agent_state.agent_speaking = True
                            logger.debug("🎤 Agent audio frame detected - speaking")

                    def on_muted():
                        agent_state.agent_speaking = False
                        logger.debug("🔇 Agent audio muted - not speaking")

                    try:
                        track.on("frame_received", on_frame_received)
                        track.on("muted", on_muted)
                        logger.info("✅ Audio frame event handlers registered")
                    except Exception as e:
                        logger.debug(f"Could not hook into audio frame events: {e}")

            room.on("track_published", on_track_published)
            room.on("track_subscribed", on_track_subscribed)
            logger.info("✅ Room track event handlers registered")
        except Exception as e:
            logger.debug(f"Could not hook into room tracks: {e}")

        # Set a default speaking state - assume agent is speaking during initial setup
        agent_state.agent_speaking = True
        logger.info("✅ Agent speaking detection setup completed")

    except Exception as e:
        logger.error(f"Error setting up agent speaking detection: {e}", exc_info=True)


def detect_printer_issue_keywords(text: str) -> Optional[str]:
    """
    Detect printer issue keywords in partial text to enable proactive search.
    
    Returns:
        Issue description if keywords detected, None otherwise
    """
    text_lower = text.lower()
    
    # Common printer issue keywords
    issue_keywords = {
        "paper": ["paper", "out of paper", "no paper", "paper jam", "jammed"],
        "ink": ["ink", "out of ink", "no ink", "ink empty", "low ink"],
        "printing": ["not printing", "won't print", "can't print", "printing issue"],
        "light": ["blinking", "light", "blinking light", "error light"],
        "error": ["error", "error message", "broken", "not working"],
        "connection": ["connection", "not connected", "offline", "disconnected"]
    }
    
    for issue_type, keywords in issue_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                # Extract context around the keyword
                words = text_lower.split()
                keyword_idx = -1
                for i, word in enumerate(words):
                    if keyword in word or word in keyword:
                        keyword_idx = i
                        break
                
                if keyword_idx >= 0:
                    # Get surrounding context (3 words before and after)
                    start = max(0, keyword_idx - 3)
                    end = min(len(words), keyword_idx + 4)
                    context = " ".join(words[start:end])
                    return context
    
    return None


async def process_user_transcript(
    transcript: str,
    analyzer: ConversationAnalyzer,
    ctx: JobContext,
    is_interim: bool = False,
) -> None:
    """
    Process a user transcript with analysis, backchanneling, and proactive search.
    
    Args:
        transcript: The transcript text to process
        analyzer: The conversation analyzer instance
        ctx: The job context
        is_interim: Whether this is an interim (partial) transcript
    """
    if not analyzer or not transcript:
        return
    
    transcript_text = transcript.strip()
    
    # Quick validation
    if len(transcript_text) <= TRANSCRIPT_MIN_LENGTH:
        return
    
    # Track user speaking time for backchanneling
    current_time = time.time()
    if agent_state.user_speaking_start_time is None:
        agent_state.user_speaking_start_time = current_time
    
    # For interim transcripts, process for proactive actions
    if is_interim:
        agent_state.interim_transcripts.append(transcript_text)
        # Keep only last 5 interim transcripts
        if len(agent_state.interim_transcripts) > 5:
            agent_state.interim_transcripts.pop(0)
        
        # Check if we should backchannel (user has been speaking for a while)
        speaking_duration = current_time - agent_state.user_speaking_start_time
        last_backchannel = agent_state.last_backchannel_time or 0
        time_since_last_backchannel = current_time - last_backchannel
        
        # Backchannel if user has been speaking for threshold and we haven't backchanneled recently
        if (speaking_duration >= BACKCHANNEL_THRESHOLD and 
            time_since_last_backchannel >= BACKCHANNEL_THRESHOLD and
            agent_state.current_session):
            try:
                backchannel = get_backchannel_phrase()
                logger.info(f"💬 Backchanneling: '{backchannel}'")
                # Send a quick backchannel response using generate_reply
                # Use a very brief instruction to minimize response time
                await agent_state.current_session.generate_reply(
                    instructions=f"Say ONLY this exact phrase, nothing else: '{backchannel}'. Keep it very brief."
                )
                agent_state.last_backchannel_time = current_time
            except Exception as e:
                logger.debug(f"Error sending backchannel: {e}")
        
        # Proactive search - detect printer issue keywords and start searching
        issue_description = detect_printer_issue_keywords(transcript_text)
        if issue_description and issue_description not in agent_state.pending_searches:
            # Start proactive search in background
            logger.info(f"🔍 Proactive search triggered for: '{issue_description[:50]}'")
            
            # Say something while searching to make it natural
            if agent_state.current_session:
                try:
                    search_phrases = [
                        "Let me check that for you",
                        "I'm looking into that",
                        "Let me see what I can find",
                        "I'm checking on that"
                    ]
                    import random
                    search_phrase = random.choice(search_phrases)
                    logger.info(f"💬 Speaking while searching: '{search_phrase}'")
                    await agent_state.current_session.generate_reply(
                        instructions=f"Say ONLY this exact phrase, nothing else: '{search_phrase}'. Keep it brief and natural."
                    )
                except Exception as e:
                    logger.debug(f"Error speaking during search: {e}")
            
            search_task = asyncio.create_task(
                proactive_printer_search(issue_description, ctx)
            )
            agent_state.pending_searches[issue_description] = search_task
        
        # Don't process interim transcripts fully, just use for proactive actions
        return
    
    # Reset speaking time for final transcripts
    agent_state.user_speaking_start_time = None
    
    # Check if already analyzed (using set for O(1) lookup)
    if transcript_text in agent_state.analyzed_transcripts:
        return
    
    # Add to analyzed set
    agent_state.add_analyzed_transcript(transcript_text)
    
    try:
        logger.info(f"📝 Captured user transcript: '{transcript_text[:100]}'")
        
        # Update personality with user response
        agent_state.personality.add_user_response(transcript_text)
        
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


async def proactive_printer_search(issue_description: str, ctx: JobContext) -> None:
    """
    Proactively search for printer issues while user is still speaking.
    
    Args:
        issue_description: Partial issue description detected
        ctx: The job context
    """
    try:
        # Wait a bit to see if we get more context
        await asyncio.sleep(0.5)
        
        # Combine with any additional interim transcripts
        if agent_state.interim_transcripts:
            combined = " ".join(agent_state.interim_transcripts[-3:])  # Last 3 interim
            if len(combined) > len(issue_description):
                issue_description = combined
        
        # Search the knowledge base proactively
        matches = agent_state.printer_kb.search_by_caller_description(issue_description)
        
        if matches:
            logger.info(f"✅ Proactive search found {len(matches)} potential matches")
            # Store results for when the agent needs them
            # The agent can access these through lookup_printer_issue
        
    except Exception as e:
        logger.debug(f"Error in proactive search: {e}")


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
    Set up transcript hooks for various message sources including interim results.
    
    Args:
        session: The agent session
        ctx: The job context
    """
    async def on_user_transcript_wrapper(transcript: str, is_interim: bool = False) -> None:
        """Wrapper for processing user transcripts (both final and interim)."""
        if agent_state.analyzer:
            await process_user_transcript(transcript, agent_state.analyzer, ctx, is_interim=is_interim)
    
    # Hook into session user messages (final transcripts)
    try:
        if hasattr(session, 'on_user_message'):
            original_handler = session.on_user_message
            
            async def wrapped_handler(message: Any) -> None:
                if original_handler:
                    await original_handler(message)
                if hasattr(message, 'content'):
                    await on_user_transcript_wrapper(message.content, is_interim=False)
            
            session.on_user_message = wrapped_handler
    except Exception as e:
        logger.debug(f"Error setting up session user message hook: {e}")
    
    # Hook into STT interim results for real-time processing
    try:
        if hasattr(session, 'stt') and hasattr(session.stt, 'on'):
            def on_interim_transcript(transcript: Any) -> None:
                """Handle interim transcription results."""
                try:
                    # Extract text from interim result
                    if hasattr(transcript, 'text'):
                        text = transcript.text
                    elif hasattr(transcript, 'alternatives') and transcript.alternatives:
                        text = transcript.alternatives[0].transcript
                    elif isinstance(transcript, str):
                        text = transcript
                    else:
                        text = str(transcript)
                    
                    if text and len(text.strip()) > TRANSCRIPT_MIN_LENGTH:
                        asyncio.create_task(on_user_transcript_wrapper(text, is_interim=True))
                except Exception as e:
                    logger.debug(f"Error processing interim transcript: {e}")
            
            # Try to hook into Deepgram interim results
            if hasattr(session.stt, 'on'):
                session.stt.on("interim_result", on_interim_transcript)
    except Exception as e:
        logger.debug(f"Error setting up interim transcript hook: {e}")
    
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
    
    # Local background MP3 playback on macOS (console testing only)
    mp3_player: Optional[subprocess.Popen] = None
    if sys.platform == "darwin":
        try:
            mp3_path = "Office Sounds 30 minutes.mp3"
            # -v 0.1 ≈ 10% volume
            mp3_player = subprocess.Popen(
                ["afplay", "-v", "0.1", mp3_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("🔊 Started local background office MP3 via afplay at ~10% volume")
        except Exception as e:
            logger.warning(f"Could not start local MP3 background playback: {e}")
    
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
        check_printer_status,
        send_test_print,
        perform_ink_cleaning,
        update_service_ticket,
        get_store_information,
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
    
    # Create agent session with real-time transcription support
    session = AgentSession(
        mcp_servers=mcp_servers,
        vad=silero.VAD.load(),
        stt=deepgram.STT(
            # Enable interim results for real-time processing
            interim_results=True,
            # Lower latency for faster response
            model="nova-3",
            language="en-US",
        ),
        llm=openai.LLM(model=session_config.llm_model),
        tts=cartesia.TTS(
            model=session_config.tts_model,
            language=session_config.tts_language,
            voice=session_config.tts_voice,
            speed=0.9,          # Slower, easier to understand
            # Use default sample rate for clearer audio; telephony path will still make it sound like a phone
        ),
    )
    
    # Store session reference for backchanneling
    agent_state.current_session = session
    
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
    
    # Set up agent speaking detection for background sounds
    setup_agent_speaking_detection(session, ctx.room)
    
    # Start background office sounds from MP3 file (20% volume)
    sound_generator = OfficeSoundGenerator(sample_rate=24000, mp3_file="Office Sounds 30 minutes.mp3")
    agent_state.background_audio_task = asyncio.create_task(
        play_background_office_sounds(ctx.room, sound_generator)
    )
    logger.info("🔊 Background office sounds from MP3 file initialized at 20% volume")
    
    # Start monitoring task
    asyncio.create_task(monitor_user_transcriptions(session, agent_state.analyzer, ctx))
    
    # Generate initial greeting following the technical support call flow
    await session.generate_reply(instructions="""
        Follow the technical support call flow script:
        
        STEP 1 - GREETING & ISSUE IDENTIFICATION:
        Say: "Thank you for calling Catalina Marketing support. How can I help you today?"
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
