import asyncio
from harness.config import Settings
from harness.llm.adapter import LLMAdapter
from harness.tools.registry import create_default_registry
from harness.llm.base import ChatMessage

async def main():
    print("Loading settings...")
    settings = Settings()
    registry = create_default_registry(".")
    adapter = LLMAdapter(
        api_key=settings.ai_api_key,
        model=settings.ai_model,
        base_url=settings.ai_base_url
    )
    
    print(f"Connecting to Ollama...")
    print(f"Model: {adapter.model}")
    print(f"Base URL: {adapter.base_url}")
    
    print("\nSending prompt to Ollama...")
    try:
        response = await adapter.generate(
            [ChatMessage(role="user", content="Hello! Are you working? Please reply with a short greeting and what model you are.")],
            tools=registry.get_openai_schemas()
        )
        print("\n✅ Success! Ollama responded with:")
        print("--------------------------------------------------")
        print(response.content)
        print("--------------------------------------------------")
    except Exception as e:
        print(f"\n❌ Error connecting to Ollama: {e}")

if __name__ == "__main__":
    asyncio.run(main())
