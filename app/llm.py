from anthropic import AsyncAnthropic
from openai import AsyncOpenAI


class LLM:
    """Thin wrapper over any OpenAI-compatible chat endpoint (Groq, Gemini, OpenRouter...)."""

    def __init__(
        self, api_key: str, base_url: str, model: str, provider: str = "groq"
    ):
        self.provider = provider.lower()
        if self.provider in {"anthropic", "claude"}:
            self.client = AsyncAnthropic(
                api_key=api_key,
                timeout=60.0,
                max_retries=0,
            )
            self.provider = "anthropic"
        elif self.provider in {"openai", "gemini", "groq", "openai-compatible"}:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=60.0,
                max_retries=0,
            )
        else:
            raise ValueError(f"unsupported LLM_PROVIDER: {provider}")
        self.model = model

    async def chat(
        self,
        system: str,
        history: list[dict],
        nudge: str | None = None,
        max_tokens: int = 400,
    ) -> str:
        if self.provider == "anthropic":
            messages = [
                {"role": item["role"], "content": item["content"]}
                for item in history
                if item["role"] in {"user", "assistant"}
            ]
            if nudge:
                messages.append({"role": "user", "content": nudge})
            response = await self.client.messages.create(
                model=self.model,
                system=system,
                messages=messages,
                temperature=0.9,
                max_tokens=max_tokens,
            )
            return "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()

        messages = [{"role": "system", "content": system}, *history]
        if nudge:
            # Used for proactive messages: a one-off instruction that is never stored.
            messages.append({"role": "user", "content": nudge})
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.9,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
