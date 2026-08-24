import json

INPUT_EXTRACTION_SYSTEM_PROMPT = """You extract structured market-analysis inputs.
Return only fields supported by the user's message. Do not invent product costs.
Convert percentage margins to a ratio between 0 and 1. Use US for the United States
and lowercase platform names. Keep product_name as the specific product being analyzed.
Put unresolved interpretations in ambiguities. Return JSON only."""

INPUT_EXTRACTION_USER_PROMPT = "Extract market analysis inputs from this request:"


def build_input_extraction_prompt(user_query: str) -> tuple[str, str]:
    payload = json.dumps({"user_query": user_query}, ensure_ascii=False)
    return INPUT_EXTRACTION_SYSTEM_PROMPT, f"{INPUT_EXTRACTION_USER_PROMPT}\n{payload}"


__all__ = ["build_input_extraction_prompt"]
