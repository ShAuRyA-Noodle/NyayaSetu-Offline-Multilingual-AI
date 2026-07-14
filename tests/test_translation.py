"""
Tests for the offline translator (M6).

Uses an injected fake LLM so the logic is tested deterministically without the
GGUF model. A separate BLEU measurement on real IITB data lives in
eval/eval_translation.py.
"""

from src.nlp.translation import OfflineTranslator


class FakeLLM:
    def __init__(self, response, success=True):
        self._response = response
        self._success = success
        self.last_call = None

    def is_available(self):
        return True

    def generate(self, prompt, system_prompt=None, temperature=None, max_tokens=None):
        self.last_call = {"prompt": prompt, "system": system_prompt}
        return {
            "success": self._success,
            "response": self._response,
            "error": "" if self._success else "boom",
            "metadata": {},
        }


def test_same_language_is_identity():
    t = OfflineTranslator(llm=FakeLLM("unused"))
    assert t.translate("hello", "en", "en") == "hello"


def test_empty_text():
    t = OfflineTranslator(llm=FakeLLM("unused"))
    assert t.translate("   ", "en", "hi") == ""


def test_basic_translation():
    t = OfflineTranslator(llm=FakeLLM("मुझे मदद चाहिए"))
    out = t.translate("I need help", "en", "hi")
    assert out == "मुझे मदद चाहिए"


def test_preamble_and_quotes_stripped():
    t = OfflineTranslator(llm=FakeLLM('Translation: "मुझे मदद चाहिए"'))
    assert t.translate("I need help", "en", "hi") == "मुझे मदद चाहिए"


def test_prompt_names_languages():
    fake = FakeLLM("output")
    OfflineTranslator(llm=fake).translate("hello", "en", "ta")
    assert "Tamil" in fake.last_call["system"]
    assert "English" in fake.last_call["system"]


def test_failure_returns_original():
    t = OfflineTranslator(llm=FakeLLM("", success=False))
    assert t.translate("keep me", "en", "hi") == "keep me"
