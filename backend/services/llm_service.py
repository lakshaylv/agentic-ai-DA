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
1. Call tools to gather data. Once you have the answer, set "complete": true.
2. Always call schema_inspector first if you need to see column names.
3. Use exact column names from the data.

Response must be ONLY a JSON object with these fields:
- "analysis": your reasoning (string)
- "next_tool": tool name to call, or null when done
- "params": {{}} for tool arguments, empty object if no args
- "complete": false while working, true when done
- "chart_type": "bar"/"line"/null
- "chart_spec": null or {{"type": "...", "x": "...", "y": "..."}}
- "insights": [] while working, or ["finding 1", "finding 2"]

Example working response: {{"analysis": "Checking schema.", "next_tool": "schema_inspector", "params": {{}}, "complete": false, "chart_type": null, "chart_spec": null, "insights": []}}
Example done response: {{"analysis": "North has the highest price at $8303.", "next_tool": null, "params": {{}}, "complete": true, "chart_type": "bar", "chart_spec": {{"type": "bar", "x": "region", "y": "price"}}, "insights": ["North region leads in total price."]}}"""


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

    max_attempts = 2
    for attempt in range(max_attempts):
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
            if attempt < max_attempts - 1:
                continue
            return LLMDecision(
                analysis=f"Failed to parse LLM response after retry: {e}",
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
    return ""


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
    kwargs = {"model": model, "messages": msgs, "temperature": 0.2}
    if "localhost" in config.base_url or "11434" in config.base_url:
        kwargs["response_format"] = {"type": "json_object"}

    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as e:
            error_str = str(e)
            if "insufficient_quota" in error_str or "rate_limit" in error_str.lower() or "rate limit" in error_str.lower():
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
                if attempt < max_attempts - 1:
                    continue
                return LLMDecision(
                    analysis="LLM returned empty response after retry",
                    next_tool=None,
                    complete=False,
                )
            cleaned = _extract_json(content)
            data = json.loads(cleaned)
            return LLMDecision(**data)
        except (json.JSONDecodeError, Exception) as e:
            if attempt < max_attempts - 1:
                continue
            return LLMDecision(
                analysis=f"Failed to parse LLM response after retry: {e}",
                next_tool=None,
                complete=False,
            )
