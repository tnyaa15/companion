from openai import AsyncOpenAI


class LLM:
    """Thin wrapper over any OpenAI-compatible chat endpoint (Groq, Gemini, OpenRouter...)."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def chat(self, system: str, history: list[dict], nudge: str | None = None) -> str:
        messages = [{"role": "system", "content": system}, *history]
        if nudge:
            # Used for proactive messages: a one-off instruction that is never stored.
            messages.append({"role": "user", "content": nudge})
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.9,
            max_tokens=400,
        )
        return (resp.choices[0].message.content or "").strip()
