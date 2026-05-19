import json
import os
from dataclasses import dataclass, field

from backend.models.schemas import LLMDecision, ToolSignature


@dataclass
class LLMConfig:
    provider: str = "openai"
    api_key: str = ""
    model: str = "deepseek/deepseek-v4-flash:free"
    base_url: str = "https://openrouter.ai/api/v1"
    tools: list[ToolSignature] = field(default_factory=list)


SYSTEM_PROMPT_TEMPLATE = """You are a data analysis agent. You do NOT manipulate dataframes directly.
You have access to these tools:

{tools_description}

Rules:
1. You MUST call at least one tool before marking complete. You cannot see the data directly.
2. Most analytical questions require multiple tool calls (inspect schema, look for missing values, group/filter).
3. Do NOT stop after a single tool call unless the query is fully answered.
4. Only set "complete": true when the data has been fully analyzed and the query is answered.

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

Respond ONLY with valid JSON. No markdown, no code fences, no extra text."""


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
    api_key = config.api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY or GEMINI_API_KEY must be set")

    tools_description = _build_tools_description(tools)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(tools_description=tools_description)

    full_messages = []
    for msg in messages:
        role = "model" if msg.get("role") == "assistant" else "user"
        text = msg.get("content", msg.get("parts", [""]))
        if isinstance(text, list):
            text = " ".join(str(p) for p in text)
        full_messages.append({"role": role, "parts": [text]})

    if config.provider == "gemini":
        return _call_gemini(full_messages, config, api_key, system_prompt=system_prompt)
    elif config.provider == "openai":
        return _call_openai(full_messages, config, api_key, system_prompt=system_prompt)
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")


def _call_gemini(
    messages: list[dict],
    config: LLMConfig,
    api_key: str,
    system_prompt: str = "",
) -> LLMDecision:
    try:
        from google import genai
    except ImportError:
        raise ImportError("google-genai not installed. Run: pip install google-genai")

    client = genai.Client(api_key=api_key)

    contents = []
    for msg in messages:
        contents.append({"role": msg["role"], "parts": [{"text": msg["parts"][0]}]})

    genai_config = {
        "response_mime_type": "application/json",
        "temperature": 0.2,
    }
    if system_prompt:
        genai_config["system_instruction"] = system_prompt

    try:
        response = client.models.generate_content(
            model=config.model,
            contents=contents,
            config=genai_config,
        )
    except Exception as e:
        error_str = str(e)
        if "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            return LLMDecision(
                analysis="LLM API quota exhausted. Please wait or switch to a different provider.",
                next_tool=None,
                complete=False,
            )
        return LLMDecision(
            analysis=f"LLM API error: {error_str}",
            next_tool=None,
            complete=False,
        )

    try:
        data = json.loads(response.text)
        return LLMDecision(**data)
    except (json.JSONDecodeError, Exception) as e:
        return LLMDecision(
            analysis=f"Failed to parse LLM response: {e}",
            next_tool=None,
            complete=False,
        )


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0] if "```" in text else text
        text = text.strip()
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        text = text[first : last + 1]
    return text


def _call_openai(
    messages: list[dict],
    config: LLMConfig,
    api_key: str,
    system_prompt: str = "",
) -> LLMDecision:
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai not installed. Run: pip install openai")

    client = OpenAI(base_url=config.base_url, api_key=api_key)

    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    for m in messages:
        role = "assistant" if m["role"] == "model" else "user"
        text = m["parts"][0]
        msgs.append({"role": role, "content": text})

    model = config.model or "deepseek/deepseek-v4-flash:free"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=msgs,
            temperature=0.2,
        )
    except Exception as e:
        error_str = str(e)
        if "insufficient_quota" in error_str or "rate_limit" in error_str.lower():
            return LLMDecision(
                analysis="LLM API rate limited or quota exhausted. Please wait or switch provider.",
                next_tool=None,
                complete=False,
            )
        return LLMDecision(
            analysis=f"LLM API error: {error_str}",
            next_tool=None,
            complete=False,
        )

    try:
        content = response.choices[0].message.content
        if not content:
            return LLMDecision(
                analysis="LLM returned empty response",
                next_tool=None,
                complete=False,
            )
        cleaned = _extract_json(content)
        data = json.loads(cleaned)
        return LLMDecision(**data)
    except (json.JSONDecodeError, Exception) as e:
        return LLMDecision(
            analysis=f"Failed to parse LLM response: {e}",
            next_tool=None,
            complete=False,
        )
