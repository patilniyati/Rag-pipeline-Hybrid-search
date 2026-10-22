import os
import time

import requests

from .settings import GenerationSettings


def _post(url, body, headers, timeout, retries=4):
    for attempt in range(retries):
        r = requests.post(url, json=body, headers=headers, timeout=timeout)
        if r.status_code in (429, 500, 503) and attempt < retries - 1:
            time.sleep(2 ** (attempt + 1))           # back off on rate limits
            continue
        if not r.ok:
            raise RuntimeError(f"LLM request failed ({r.status_code}): {r.text[:300]}")
        return r.json()


class LLM:
    def generate(self, prompt: str, system: str = "", json_mode: bool = False) -> str:
        raise NotImplementedError


class GeminiLLM(LLM):
    def __init__(self, s: GenerationSettings):
        from dotenv import load_dotenv
        load_dotenv()
        self.key = os.getenv(s.api_key_env)
        if not self.key:
            raise RuntimeError(f"{s.api_key_env} is missing. Add it to your .env file.")
        self.s = s

    def generate(self, prompt, system="", json_mode=False):
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": self.s.temperature}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.s.model}:generateContent")
        data = _post(url, body, {"x-goog-api-key": self.key}, self.s.timeout_s)
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Gemini returned no text (blocked or empty): {str(data)[:300]}")


class OllamaLLM(LLM):
    def __init__(self, s: GenerationSettings):
        self.s = s

    def generate(self, prompt, system="", json_mode=False):
        messages = ([{"role": "system", "content": system}] if system else [])
        messages.append({"role": "user", "content": prompt})
        body = {"model": self.s.model, "messages": messages, "stream": False,
                "options": {"temperature": self.s.temperature}}
        if json_mode:
            body["format"] = "json"
        data = _post(f"{self.s.ollama_url}/api/chat", body, {}, self.s.timeout_s)
        return data["message"]["content"]

class GroqLLM(LLM):
    def __init__(self, s: GenerationSettings):
        from dotenv import load_dotenv
        load_dotenv()
        self.key = os.getenv(s.api_key_env)
        if not self.key:
            raise RuntimeError(f"{s.api_key_env} is missing. Add it to your .env file.")
        self.s = s

    def generate(self, prompt, system="", json_mode=False):
        messages = ([{"role": "system", "content": system}] if system else [])
        messages.append({"role": "user", "content": prompt})
        body = {"model": self.s.model, "messages": messages,
                "temperature": self.s.temperature}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        data = _post("https://api.groq.com/openai/v1/chat/completions", body,
                     {"Authorization": f"Bearer {self.key}"}, self.s.timeout_s)
        return data["choices"][0]["message"]["content"]


def make_llm(s: GenerationSettings) -> LLM:
    if s.provider == "gemini":
        return GeminiLLM(s)
    if s.provider == "ollama":
        return OllamaLLM(s)
    if s.provider == "groq":
        return GroqLLM(s)
    raise ValueError(f"Unknown provider: {s.provider}")