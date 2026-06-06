import json
from typing import Any

import httpx

from .settings import LLMSettings


class LLMAnalysisError(RuntimeError):
    pass


def extract_responses_output_text(response_data: dict[str, Any]) -> str:
    if isinstance(response_data.get("output_text"), str):
        return response_data["output_text"]

    for item in response_data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"]
    raise LLMAnalysisError("模型响应中没有可解析的文本结果")


def extract_chat_output_text(response_data: dict[str, Any]) -> str:
    choices = response_data.get("choices", [])
    if choices:
        content = choices[0].get("message", {}).get("content")
        if isinstance(content, str):
            return content
    raise LLMAnalysisError("模型响应中没有可解析的聊天结果")


def request_structured_output(
    settings: LLMSettings,
    instructions: str,
    input_text: str,
    schema: dict,
    schema_name: str,
    client: httpx.Client | None = None,
) -> str:
    owns_client = client is None
    client = client or httpx.Client(timeout=settings.timeout_seconds)

    if settings.api_style == "chat-completions":
        endpoint = f"{settings.base_url}/chat/completions"
        payload = {
            "model": settings.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{instructions}\n"
                        "你必须只返回一个符合下方 JSON Schema 的 JSON 对象，不要输出 Markdown 或解释文字。\n"
                        f"JSON Schema（{schema_name}）：{json.dumps(schema, ensure_ascii=False)}"
                    ),
                },
                {"role": "user", "content": input_text},
            ],
            "response_format": {"type": "json_object"},
        }
    elif settings.api_style == "responses":
        endpoint = f"{settings.base_url}/responses"
        payload = {
            "model": settings.model,
            "store": False,
            "instructions": instructions,
            "input": input_text,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
        }
    else:
        raise LLMAnalysisError(f"不支持的大模型 API 风格：{settings.api_style}")

    try:
        response = client.post(
            endpoint,
            headers={"Authorization": f"Bearer {settings.api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        response_data = response.json()
        if settings.api_style == "chat-completions":
            return extract_chat_output_text(response_data)
        return extract_responses_output_text(response_data)
    except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
        raise LLMAnalysisError("大模型请求失败或返回格式无效") from exc
    finally:
        if owns_client:
            client.close()
