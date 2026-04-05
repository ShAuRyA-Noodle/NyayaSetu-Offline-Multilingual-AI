"""
Intent Engine — Classify user voice intents and extract entities using sarvam-m-tools.
"""

import json
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from .config import NyayaVaaniConfig
from .language_registry import LanguageRegistry

logger = logging.getLogger(__name__)


INTENT_TYPES = [
    "submit_grievance",
    "check_status",
    "browse_schemes",
    "ask_eligibility",
    "hear_notice",
    "general_query",
    "unclear",
]


@dataclass
class IntentResult:
    intent: str
    confidence: float
    entities: dict = field(default_factory=dict)
    language: str = "hi"


@dataclass
class VoiceGrievanceData:
    title: str
    description: str
    category: str
    language: str
    citizen_location: Optional[str] = None
    extracted_entities: dict = field(default_factory=dict)


class IntentEngine:
    """Voice intent classification and entity extraction."""

    def __init__(self, config: NyayaVaaniConfig):
        self.config = config

    async def classify_intent(self, text: str, language: str = "hi") -> IntentResult:
        """Classify user intent from transcribed text."""
        prompt = f"""You are an intent classifier for a government services platform (NyayaSetu).
Classify the following citizen's speech into one of these intents:
- submit_grievance: citizen wants to file a complaint
- check_status: citizen wants to check grievance status
- browse_schemes: citizen wants to know about government schemes
- ask_eligibility: citizen asking about eligibility for a scheme
- hear_notice: citizen wants to hear/read notices
- general_query: general question
- unclear: cannot determine intent

Also extract entities like: scheme_name, grievance_id, department, location, category.

Citizen's text (language: {language}):
"{text}"

Return ONLY a JSON object:
{{"intent": "one_of_the_intents", "confidence": 0.0_to_1.0, "entities": {{"key": "value"}}}}"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.config.ollama_base_url}/api/generate",
                    json={
                        "model": self.config.sarvam_m_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 300},
                    },
                )
                response.raise_for_status()
                data = response.json()

            raw = data.get("response", "").strip()
            parsed = self._parse_json_response(raw)

            intent = parsed.get("intent", "unclear")
            if intent not in INTENT_TYPES:
                intent = "unclear"

            return IntentResult(
                intent=intent,
                confidence=min(float(parsed.get("confidence", 0.5)), 1.0),
                entities=parsed.get("entities", {}),
                language=language,
            )
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return IntentResult(intent="unclear", confidence=0.0, language=language)

    async def extract_grievance_from_voice(
        self, text: str, language: str = "hi"
    ) -> VoiceGrievanceData:
        """Extract structured grievance data from voice transcription."""
        prompt = f"""Extract structured grievance information from the following citizen's voice complaint.

Citizen's text (language: {language}):
"{text}"

Return ONLY a JSON object:
{{
  "title": "brief title in English (10 words max)",
  "description": "full complaint text (keep original language, clean up speech artifacts)",
  "category": "one of: payment_delays, eligibility_questions, service_denial, document_issues, application_rejection, corruption, infrastructure, other",
  "location": "extracted location or null",
  "entities": {{"scheme_name": "if mentioned", "department": "if mentioned"}}
}}"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.config.ollama_base_url}/api/generate",
                    json={
                        "model": self.config.sarvam_m_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 400},
                    },
                )
                response.raise_for_status()
                data = response.json()

            raw = data.get("response", "").strip()
            parsed = self._parse_json_response(raw)

            return VoiceGrievanceData(
                title=parsed.get("title", "Voice Grievance"),
                description=parsed.get("description", text),
                category=parsed.get("category", "other"),
                language=language,
                citizen_location=parsed.get("location"),
                extracted_entities=parsed.get("entities", {}),
            )
        except Exception as e:
            logger.error(f"Grievance extraction failed: {e}")
            return VoiceGrievanceData(
                title="Voice Grievance",
                description=text,
                category="other",
                language=language,
            )

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        """Parse JSON from LLM response, handling common issues."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # Try extracting JSON block
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {}
