"""Small OpenAI-compatible JSON client with no third-party runtime dependency."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class AIProviderError(RuntimeError):
    """Raised when the configured AI provider cannot return usable JSON."""


def load_env_file(path: Path) -> None:
    """Load a minimal .env file without overriding real environment variables."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def extract_json(text: str) -> dict[str, Any]:
    content = text.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end <= start:
            raise AIProviderError("AI 未返回 JSON 对象") from None
        try:
            parsed = json.loads(content[start : end + 1])
        except json.JSONDecodeError as error:
            raise AIProviderError("AI 返回的 JSON 无法解析") from error
    if not isinstance(parsed, dict):
        raise AIProviderError("AI 返回结果必须是 JSON 对象")
    return parsed


@dataclass(frozen=True)
class AIClient:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int = 45
    json_mode: bool = True
    thinking: str = "disabled"

    @classmethod
    def from_environment(cls, root: Path) -> "AIClient":
        load_env_file(root / ".env")
        api_key = os.environ.get("AI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("AI_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("AI_MODEL") or os.environ.get("OPENAI_MODEL", "")
        timeout = int(os.environ.get("AI_TIMEOUT_SECONDS", "45"))
        json_mode = os.environ.get("AI_JSON_MODE", "true").strip().lower() not in {"0", "false", "no", "off"}
        thinking = os.environ.get("AI_THINKING", "disabled").strip().lower()
        if thinking not in {"enabled", "disabled"}:
            thinking = "disabled"
        return cls(
            api_key=api_key.strip(),
            base_url=base_url.rstrip("/"),
            model=model.strip(),
            timeout_seconds=timeout,
            json_mode=json_mode,
            thinking=thinking,
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    @property
    def endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def chat_json(self, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            raise AIProviderError("AI 尚未配置")
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "temperature": 0.2,
            "thinking": {"type": self.thinking},
            "max_tokens": 4096,
        }
        if self.json_mode:
            request_body["response_format"] = {"type": "json_object"}
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "baili-electronics/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise AIProviderError(f"AI 服务返回 HTTP {error.code}：{detail}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise AIProviderError(f"无法连接 AI 服务：{error}") from error
        except json.JSONDecodeError as error:
            raise AIProviderError("AI 服务响应不是有效 JSON") from error

        try:
            content = response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise AIProviderError("AI 服务响应缺少 choices[0].message.content") from error
        if isinstance(content, list):
            content = "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content)
        return extract_json(str(content))
