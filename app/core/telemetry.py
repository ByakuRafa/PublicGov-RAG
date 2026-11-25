"""Utilitários de telemetria para extração de tokens e estimativa de custo de LLMs."""

from typing import Any, Dict, Iterable, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage

from app.core.config import settings

# Valores de referência em USD por 1 milhão de tokens (input_per_1m, output_per_1m)
MODEL_PRICING_PER_1M_USD: Dict[str, Tuple[float, float]] = {
    "gemini-3.5-flash-lite": (0.10, 0.40),
    "gemini-3.5-flash": (0.15, 0.60),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.0-flash-lite": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _extract_usage_from_message(msg: AIMessage) -> Tuple[int, int]:
    """Extrai (prompt_tokens, completion_tokens) de uma AIMessage LangChain."""
    usage = getattr(msg, "usage_metadata", None)
    if isinstance(usage, dict):
        in_tok = _safe_int(usage.get("input_tokens") or usage.get("prompt_tokens"))
        out_tok = _safe_int(usage.get("output_tokens") or usage.get("completion_tokens"))
        if in_tok or out_tok:
            return in_tok, out_tok

    resp_meta = getattr(msg, "response_metadata", None)
    if isinstance(resp_meta, dict):
        for key in ("usage_metadata", "token_usage"):
            nested = resp_meta.get(key)
            if isinstance(nested, dict):
                in_tok = _safe_int(
                    nested.get("prompt_token_count")
                    or nested.get("input_tokens")
                    or nested.get("prompt_tokens")
                )
                out_tok = _safe_int(
                    nested.get("candidates_token_count")
                    or nested.get("output_tokens")
                    or nested.get("completion_tokens")
                )
                if in_tok or out_tok:
                    return in_tok, out_tok

    return 0, 0


def extract_token_usage(messages: Iterable[BaseMessage]) -> Tuple[int, int]:
    """Soma prompt_tokens e completion_tokens de todas as AIMessages do grafo."""
    total_prompt = 0
    total_completion = 0
    for msg in messages:
        if isinstance(msg, AIMessage):
            p_tok, c_tok = _extract_usage_from_message(msg)
            total_prompt += p_tok
            total_completion += c_tok
    return total_prompt, total_completion


def _resolve_model_pricing(model_name: str) -> Optional[Tuple[float, float]]:
    if (
        settings.LLM_INPUT_COST_PER_1M_USD is not None
        and settings.LLM_OUTPUT_COST_PER_1M_USD is not None
    ):
        return (
            float(settings.LLM_INPUT_COST_PER_1M_USD),
            float(settings.LLM_OUTPUT_COST_PER_1M_USD),
        )

    normalized = (model_name or "").strip().lower()
    if normalized.startswith("models/"):
        normalized = normalized[len("models/"):]

    if normalized in MODEL_PRICING_PER_1M_USD:
        return MODEL_PRICING_PER_1M_USD[normalized]

    for prefix, pricing in MODEL_PRICING_PER_1M_USD.items():
        if normalized.startswith(prefix):
            return pricing

    # Fallback por família Gemini para variantes/versões mais novas
    if "gemini" in normalized:
        if "flash-lite" in normalized:
            return (0.10, 0.40)
        if "flash" in normalized:
            return (0.15, 0.60)
        if "pro" in normalized:
            return (1.25, 10.00)
    return None


def estimate_llm_cost_usd(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Calcula custo estimado da chamada em USD a partir do modelo e contagem de tokens."""
    pricing = _resolve_model_pricing(model_name)
    if pricing is None:
        return 0.0

    input_rate, output_rate = pricing
    cost = (
        (_safe_int(prompt_tokens) / 1_000_000.0) * input_rate
        + (_safe_int(completion_tokens) / 1_000_000.0) * output_rate
    )
    return round(cost, 6)
