import json
import os
from dataclasses import dataclass, field

from backend.models.schemas import LLMDecision, ToolSignature


@dataclass
class LLMConfig:
    provider: str = "gemini"
    api_key: str = ""
    model: str = "gemini-2.5-flash-lite"
    tools: list[ToolSignature] = field(default_factory=list)


SYSTEM_PROMPT_TEMPLATE = """You are a data analysis agent. You do NOT manipulate dataframes directly.
You have access to these tools:

{tools_description}

Always respond in JSON with this exact structure:
{{
  "analysis": "your reasoning about the current state",
  "next_tool": "tool_name or null if analysis is complete",
  "params": {{ ... }},
  "complete": false,
  "chart_type": null,
  "chart_spec": null,
  "insights": []
}}

If the analysis is complete, set "complete" to true, provide chart and insight data, and set next_tool to null."""


def _build_tools_description(tools: list[ToolSignature]) -> str:
    if not tools:
        return "  (no tools available)"
    lines = []
    for t in tools:
        params_str = json.dumps(t.params_schema, indent=4)
        lines.append(f"  - {t.name}: {t.description}\n    Parameters schema:\n{params_str}")
    return "\n".join(lines)


def analyze(
    messages: list[dict],
    tools: list[ToolSignature],
    config: LLMConfig,
) -> LLMDecision:
    api_key = config.api_key or os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("LLM_API_KEY or GEMINI_API_KEY must be set")

    tools_description = _build_tools_description(tools)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(tools_description=tools_description)

    full_messages = [{"role": "user", "parts": [system_prompt]}]
    for msg in messages:
        role = "user" if msg.get("role") in ("user", "system") else "user"
        text = msg.get("content", msg.get("parts", [""]))
        if isinstance(text, list):
            text = " ".join(str(p) for p in text)
        full_messages.append({"role": role, "parts": [text]})

    if config.provider == "gemini":
        return _call_gemini(full_messages, config, api_key)
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")


def _call_gemini(
    messages: list[dict],
    config: LLMConfig,
    api_key: str,
) -> LLMDecision:
    try:
        from google import genai
    except ImportError:
        raise ImportError("google-genai not installed. Run: pip install google-genai")

    client = genai.Client(api_key=api_key)

    contents = []
    for msg in messages:
        contents.append({"role": "user", "parts": [{"text": msg["parts"][0]}]})

    try:
        response = client.models.generate_content(
            model=config.model,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        )
    except Exception as e:
        error_str = str(e)
        if "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            return LLMDecision(
                analysis="LLM API quota exhausted. Please wait or switch to a different provider.",
                next_tool=None,
                complete=True,
            )
        return LLMDecision(
            analysis=f"LLM API error: {error_str}",
            next_tool=None,
            complete=True,
        )

    try:
        data = json.loads(response.text)
        return LLMDecision(**data)
    except (json.JSONDecodeError, Exception) as e:
        return LLMDecision(
            analysis=f"Failed to parse LLM response: {e}",
            next_tool=None,
            complete=True,
        )
