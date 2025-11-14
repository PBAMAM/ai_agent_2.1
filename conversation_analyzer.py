import asyncio
import logging
import numpy as np
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum
from livekit import rtc
from livekit.agents import AgentSession
from livekit.plugins import openai
import json

logger = logging.getLogger("conversation-analyzer")


class ConversationQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    NEUTRAL = "neutral"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class ConversationMetrics:
    sentiment_score: float
    quality: ConversationQuality
    raised_voice_detected: bool
    negative_indicators: list[str]
    audio_level_avg: float
    audio_level_max: float
    warning_count: int


class ConversationAnalyzer:
    def __init__(
        self,
        session: AgentSession,
        room: rtc.Room,
        on_quality_change: Optional[Callable[[ConversationMetrics], None]] = None,
        audio_threshold: float = 0.7,
    ):
        self.session = session
        self.room = room
        self.on_quality_change = on_quality_change
        self.audio_threshold = audio_threshold
        
        self.metrics = ConversationMetrics(
            sentiment_score=0.0,
            quality=ConversationQuality.NEUTRAL,
            raised_voice_detected=False,
            negative_indicators=[],
            audio_level_avg=0.0,
            audio_level_max=0.0,
            warning_count=0,
        )
        
        self.audio_levels = []
        self.conversation_history = []
        self.llm = openai.LLM(model="gpt-4o-mini")
        
        self.negative_keywords = [
            "angry", "frustrated", "upset", "complaint", "terrible", "awful",
            "horrible", "disappointed", "unacceptable", "ridiculous", "stupid",
            "hate", "worst", "refund", "cancel", "sue", "lawyer", "manager",
            "supervisor", "complaint", "dissatisfied", "not happy", "very upset"
        ]
        
        self._setup_audio_monitoring()
        self._setup_transcription_monitoring()
    
    def _setup_audio_monitoring(self):
        async def on_track_subscribed_async(
            track: rtc.RemoteAudioTrack,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ):
            if isinstance(track, rtc.RemoteAudioTrack):
                async def on_audio_frame(frame: rtc.AudioFrame):
                    try:
                        audio_data = np.frombuffer(frame.data, dtype=np.int16)
                        if len(audio_data) > 0:
                            rms = np.sqrt(np.mean(audio_data**2))
                            normalized_level = min(rms / 32768.0, 1.0)
                            
                            self.audio_levels.append(normalized_level)
                            if len(self.audio_levels) > 100:
                                self.audio_levels.pop(0)
                            
                            if len(self.audio_levels) > 10:
                                avg_level = np.mean(self.audio_levels[-20:])
                                max_level = np.max(self.audio_levels[-20:])
                                
                                self.metrics.audio_level_avg = avg_level
                                self.metrics.audio_level_max = max_level
                                
                                if max_level > self.audio_threshold:
                                    if not self.metrics.raised_voice_detected:
                                        self.metrics.raised_voice_detected = True
                                        self.metrics.warning_count += 1
                                        logger.warning(
                                            f"⚠️ RAISED VOICE DETECTED! Audio level: {max_level:.2f} "
                                            f"(threshold: {self.audio_threshold})"
                                        )
                                        self._notify_quality_change()
                                else:
                                    if self.metrics.raised_voice_detected and max_level < self.audio_threshold * 0.8:
                                        self.metrics.raised_voice_detected = False
                    except Exception as e:
                        logger.error(f"Error processing audio frame: {e}")
                
                track.on("frame_received", on_audio_frame)
        
        # Wrap async callback in a synchronous function
        def on_track_subscribed(
            track: rtc.RemoteAudioTrack,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ):
            asyncio.create_task(on_track_subscribed_async(track, publication, participant))
        
        self.room.on("track_subscribed", on_track_subscribed)
    
    def _setup_transcription_monitoring(self):
        async def analyze_transcription(text: str, is_agent: bool = False):
            if not text or len(text.strip()) < 3:
                return
            
            self.conversation_history.append({
                "text": text,
                "is_agent": is_agent,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            if len(self.conversation_history) > 50:
                self.conversation_history.pop(0)
            
            if not is_agent:
                await self._analyze_sentiment(text)
                await self._detect_negative_indicators(text)
        
        self._analyze_transcription = analyze_transcription
    
    async def _analyze_sentiment(self, text: str):
        try:
            logger.info(f"🔍 Analyzing sentiment for: '{text[:50]}...'")
            prompt = f"""Analyze the sentiment of this customer statement on a scale from -1 (very negative) to 1 (very positive). 
Return only a JSON object with "score" (float) and "reason" (string).

Customer statement: "{text}"

JSON response:"""
            
            response = await self.llm.chat.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            sentiment_score = float(result.get("score", 0.0))
            reason = result.get("reason", "")
            
            self.metrics.sentiment_score = sentiment_score
            
            logger.info(f"💭 Sentiment Analysis Result: Score={sentiment_score:.2f}, Reason={reason}")
            
            if sentiment_score < -0.5:
                self.metrics.warning_count += 1
                logger.warning(
                    f"⚠️ NEGATIVE SENTIMENT DETECTED! Score: {sentiment_score:.2f} - {reason}"
                )
                logger.warning(f"Customer said: {text}")
            
            self._update_quality()
            self._notify_quality_change()
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            logger.debug(f"Sentiment analysis error details: {str(e)}")
    
    async def _detect_negative_indicators(self, text: str):
        text_lower = text.lower()
        detected_indicators = []
        
        for keyword in self.negative_keywords:
            if keyword in text_lower:
                detected_indicators.append(keyword)
        
        if detected_indicators:
            self.metrics.negative_indicators.extend(detected_indicators)
            self.metrics.warning_count += 1
            logger.warning(
                f"⚠️ NEGATIVE KEYWORDS DETECTED: {', '.join(detected_indicators)}"
            )
            logger.warning(f"Customer said: {text}")
            self._update_quality()
            self._notify_quality_change()
        else:
            logger.debug(f"✅ No negative keywords detected in: '{text[:50]}...'")
    
    def _update_quality(self):
        score = self.metrics.sentiment_score
        has_raised_voice = self.metrics.raised_voice_detected
        has_negative_indicators = len(self.metrics.negative_indicators) > 0
        warning_count = self.metrics.warning_count
        
        if score < -0.7 or warning_count >= 3:
            self.metrics.quality = ConversationQuality.CRITICAL
        elif score < -0.4 or has_raised_voice or (has_negative_indicators and warning_count >= 2):
            self.metrics.quality = ConversationQuality.POOR
        elif score < -0.1 or has_negative_indicators:
            self.metrics.quality = ConversationQuality.NEUTRAL
        elif score > 0.6:
            self.metrics.quality = ConversationQuality.EXCELLENT
        elif score > 0.3:
            self.metrics.quality = ConversationQuality.GOOD
        else:
            self.metrics.quality = ConversationQuality.NEUTRAL
    
    def _notify_quality_change(self):
        if self.on_quality_change:
            try:
                self.on_quality_change(self.metrics)
            except Exception as e:
                logger.error(f"Error in quality change callback: {e}")
        
        quality_emoji = {
            ConversationQuality.EXCELLENT: "✅",
            ConversationQuality.GOOD: "👍",
            ConversationQuality.NEUTRAL: "➖",
            ConversationQuality.POOR: "⚠️",
            ConversationQuality.CRITICAL: "🚨",
        }
        
        emoji = quality_emoji.get(self.metrics.quality, "➖")
        logger.info(
            f"{emoji} Conversation Quality: {self.metrics.quality.value.upper()} | "
            f"Sentiment: {self.metrics.sentiment_score:.2f} | "
            f"Raised Voice: {self.metrics.raised_voice_detected} | "
            f"Warnings: {self.metrics.warning_count}"
        )
    
    async def analyze_text(self, text: str, is_agent: bool = False):
        await self._analyze_transcription(text, is_agent)
    
    def get_metrics(self) -> ConversationMetrics:
        return self.metrics
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            "quality": self.metrics.quality.value,
            "sentiment_score": self.metrics.sentiment_score,
            "raised_voice_detected": self.metrics.raised_voice_detected,
            "negative_indicators": list(set(self.metrics.negative_indicators)),
            "audio_level_avg": self.metrics.audio_level_avg,
            "audio_level_max": self.metrics.audio_level_max,
            "warning_count": self.metrics.warning_count,
            "conversation_turns": len(self.conversation_history),
        }

