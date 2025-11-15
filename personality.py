"""
Adaptive Personality Engine
Adjusts conversation style based on user behavior
Based on CATALINA_AI_VOICE_AGENT_DESIGN.md specifications
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class AdaptivePersonality:
    """
    Dynamically adjusts response style based on user cooperation and behavior
    """
    
    def __init__(self):
        self.cooperation_score = 50  # 0-100 scale
        self.technical_level = 50     # How technical to be
        self.urgency = 50             # How quickly to move
        self.user_responses: List[str] = []
    
    def update(self, new_score: int):
        """Update cooperation score"""
        self.cooperation_score = max(0, min(100, new_score))
    
    def assess_cooperation(self, user_responses: List[str]) -> int:
        """
        Analyze user responses to gauge cooperation level
        """
        if not user_responses:
            return self.cooperation_score
        
        signals = {
            "positive": ["okay", "sure", "yes", "got it", "done", "ready", "yes", "yep", "alright", "perfect"],
            "hesitant": ["busy", "later", "not now", "in a rush", "can't", "maybe", "not sure"],
            "confused": ["what", "how", "don't understand", "where", "huh", "repeat"],
            "frustrated": ["already did", "not working", "still broken", "ugh", "frustrated", "annoyed"]
        }
        
        score_adjustment = 0
        
        for response in user_responses[-5:]:  # Look at last 5 responses
            response_lower = response.lower()
            
            # Check for positive signals
            for positive_word in signals["positive"]:
                if positive_word in response_lower:
                    score_adjustment += 5
                    break
            
            # Check for hesitant signals
            for hesitant_word in signals["hesitant"]:
                if hesitant_word in response_lower:
                    score_adjustment -= 10
                    break
            
            # Check for confused signals
            for confused_word in signals["confused"]:
                if confused_word in response_lower:
                    score_adjustment -= 5
                    break
            
            # Check for frustrated signals
            for frustrated_word in signals["frustrated"]:
                if frustrated_word in response_lower:
                    score_adjustment -= 15
                    break
        
        # Update cooperation score
        new_score = self.cooperation_score + score_adjustment
        self.cooperation_score = max(0, min(100, new_score))
        
        return self.cooperation_score
    
    def add_user_response(self, response: str):
        """Add a user response and update cooperation score"""
        if response:
            self.user_responses.append(response)
            # Keep only last 20 responses
            if len(self.user_responses) > 20:
                self.user_responses.pop(0)
            
            # Reassess cooperation
            self.assess_cooperation(self.user_responses)
    
    def get_style_adjustments(self, cooperation_score: Optional[int] = None) -> Dict:
        """
        Return style adjustments based on cooperation
        """
        if cooperation_score is None:
            cooperation_score = self.cooperation_score
        
        if cooperation_score > 70:
            return {
                "pace": "efficient",
                "detail_level": "moderate",
                "empathy": "standard",
                "acknowledgments": "brief",
                "tone": "friendly and appreciative",
                "filler_words": "minimal",
                "encouragement": "occasional"
            }
        elif cooperation_score < 40:
            return {
                "pace": "patient",
                "detail_level": "high",
                "empathy": "enhanced",
                "acknowledgments": "enthusiastic",
                "tone": "very patient and understanding",
                "filler_words": "more frequent",
                "encouragement": "frequent"
            }
        else:
            return {
                "pace": "balanced",
                "detail_level": "moderate",
                "empathy": "standard",
                "acknowledgments": "standard",
                "tone": "friendly and professional",
                "filler_words": "moderate",
                "encouragement": "moderate"
            }
    
    def get_natural_phrases(self, context: str) -> List[str]:
        """
        Get natural phrases based on context and cooperation level
        """
        style = self.get_style_adjustments()
        
        phrases = {
            "acknowledging": {
                "efficient": ["Okay", "Got it", "Perfect"],
                "balanced": ["Okay, I understand", "Got it, thanks", "Perfect, thank you"],
                "patient": ["Okay, I totally understand", "I hear you, and I appreciate your patience", "Thank you so much for working with me on this"]
            },
            "thinking": {
                "efficient": ["Let me check", "One moment"],
                "balanced": ["Let me check on that for you", "Give me just a second"],
                "patient": ["Let me take a look at that for you", "Give me just a moment while I check"]
            },
            "encouraging": {
                "efficient": ["Good", "Nice"],
                "balanced": ["Good job", "You're doing great"],
                "patient": ["You're doing great", "Perfect, you're doing exactly what we need", "I really appreciate your patience with this"]
            },
            "empathy": {
                "efficient": [],
                "balanced": ["I understand this can be frustrating"],
                "patient": ["I know this is frustrating, and I really appreciate your patience", "I understand how inconvenient this is, especially when you're busy"]
            }
        }
        
        pace_key = style["pace"]
        
        if context in phrases:
            return phrases[context].get(pace_key, phrases[context]["balanced"])
        
        return []
    
    def reset(self):
        """Reset personality state"""
        self.cooperation_score = 50
        self.technical_level = 50
        self.urgency = 50
        self.user_responses = []

