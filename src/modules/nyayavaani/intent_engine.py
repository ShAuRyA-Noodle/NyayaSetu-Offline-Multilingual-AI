"""
Intent Engine — Classify user voice intents and extract entities.
Uses the shared LLM client (Groq cloud or Ollama local).
"""

import json
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from .config import NyayaVaaniConfig

# Sanitize transcribed citizen text before it lands in an LLM prompt.
try:
    from src.generation.prompt_templates import sanitize_user_input
except ImportError:
    # Fallback no-op so this module never hard-fails on import.
    def sanitize_user_input(text: str, max_len: int = 4000) -> str:  # type: ignore
        return (text or "")[:max_len]

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

    def _get_llm_client(self):
        from src.generation.llm_client import create_client
        return create_client()

    async def classify_intent(self, text: str, language: str = "hi") -> IntentResult:
        """Classify user intent from transcribed text."""
        # Strip jailbreak markers from transcribed audio before prompting.
        safe_text = sanitize_user_input(text, max_len=2000)
        prompt = f"""You are an intent classifier for an Indian government services platform (NyayaSetu).
The citizen is speaking in {language}. Classify their speech into one of these intents:
- submit_grievance: citizen wants to file a complaint or report a problem
- check_status: citizen wants to check grievance/application status
- browse_schemes: citizen wants to know about government schemes
- ask_eligibility: citizen asking about eligibility for a scheme
- hear_notice: citizen wants to hear/read official notices
- general_query: general question about government services
- unclear: cannot determine intent

Also extract entities like: scheme_name, grievance_id, department, location, category.

Citizen's text:
"{safe_text}"

Return ONLY a JSON object:
{{"intent": "one_of_the_intents", "confidence": 0.0_to_1.0, "entities": {{"key": "value"}}}}"""

        try:
            client = self._get_llm_client()
            result = client.generate(
                prompt=prompt,
                system_prompt="You are a multilingual intent classifier for Indian government services. You understand Hindi, Tamil, Bengali, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese, Urdu, and English. Return ONLY valid JSON.",
                temperature=0.1,
                max_tokens=300,
            )

            if not result.get("success"):
                raise RuntimeError(result.get("error", "LLM failed"))

            raw = result["response"].strip()
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
        safe_text = sanitize_user_input(text, max_len=5000)
        prompt = f"""Extract structured grievance information from the following citizen's voice complaint.

Citizen's text (language: {language}):
"{safe_text}"

Return ONLY a JSON object:
{{
  "title": "brief title in English (10 words max)",
  "description": "full complaint text (keep original language, clean up speech artifacts)",
  "category": "one of: payment_delays, eligibility_questions, service_denial, document_issues, application_rejection, corruption, infrastructure, other",
  "location": "extracted location or null",
  "entities": {{"scheme_name": "if mentioned", "department": "if mentioned"}}
}}"""

        try:
            client = self._get_llm_client()
            result = client.generate(
                prompt=prompt,
                system_prompt="You are an Indian government grievance analyst. Extract structured data from citizen complaints in any Indian language. Return ONLY valid JSON.",
                temperature=0.1,
                max_tokens=400,
            )

            if not result.get("success"):
                raise RuntimeError(result.get("error", "LLM failed"))

            raw = result["response"].strip()
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
        """Parse JSON from LLM response, handling common issues.

        The previous regex `\\{[\\s\\S]*\\}` is greedy: if the model emits
        any prose containing braces (e.g. "{example}") AFTER the real JSON,
        it slurps everything between the first `{` and the FINAL `}`,
        producing an unparseable blob. We do two things instead:

        1. Try direct json.loads on the trimmed payload.
        2. Walk the string and extract the first balanced `{...}` block.
        """
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Balanced-brace scanner: find the first `{` and read until depth 0,
        # ignoring braces inside string literals.
        depth = 0
        start: Optional[int] = None
        in_str = False
        esc = False
        for i, ch in enumerate(raw):
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                if start is None:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    candidate = raw[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        # Reset and keep looking for a later balanced block.
                        start = None
        # Final non-greedy fallback for malformed-but-close payloads.
        json_match = re.search(r'\{[\s\S]*?\}', raw)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {}
