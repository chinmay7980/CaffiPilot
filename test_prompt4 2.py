import asyncio
import os
from pathlib import Path
import tempfile
from harness.tools.registry import create_default_registry
from harness.tools.file_tools import resolve_safe_path
from harness.llm.base import ChatMessage
from harness.llm.adapter import LLMAdapter
from harness.config import Settings

async def run_security_tests():
    print("--- 1. Testing Path Traversal ---")
    try:
        resolve_safe_path(".", "../outside.txt")
        print("❌ Path traversal succeeded (BAD)")
    except ValueError as e:
        print(f"✅ Path traversal blocked: {e}")

    print("\n--- 2. Testing Absolute Paths Outside Workspace ---")
    try:
        resolve_safe_path(".", "/etc/passwd")
        print("❌ Absolute path succeeded (BAD)")
    except ValueError as e:
        print(f"✅ Absolute path blocked: {e}")
        
    print("\n--- 3. Testing Symlinks Outside Workspace ---")
    # Create temp workspace
    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td)
        outside = Path(tempfile.gettempdir()) / "outside_secret.txt"
        with open(outside, "w") as f:
            f.write("secret")
        
        symlink = workspace / "link_to_outside"
        try:
            os.symlink(outside, symlink)
            try:
                resolve_safe_path(str(workspace), "link_to_outside")
                print("❌ Symlink outside succeeded (BAD)")
            except ValueError as e:
                print(f"✅ Symlink outside blocked: {e}")
        except OSError:
            print("⚠️ Could not create symlink, skipping test.")
            
        if outside.exists():
            outside.unlink()

    print("\n--- 4. Testing Binary/Large Files ---")
    registry = create_default_registry(".")
    read_tool = registry.get("read_file")
    
    # create a mock binary file
    with open("dummy.bin", "wb") as f:
        f.write(os.urandom(1024))
    
    res = await read_tool.execute(path="dummy.bin")
    if res.success:
        print("✅ Read binary file (handled via errors='replace')")
    else:
        print(f"❌ Failed to read binary: {res.error}")
        
    os.unlink("dummy.bin")
    
    print("\n--- 5. Testing Missing Files ---")
    res = await read_tool.execute(path="does_not_exist_at_all_123.txt")
    if not res.success and "not found" in res.error:
        print(f"✅ Handled missing file: {res.error}")
    else:
        print("❌ Missing file behavior incorrect.")

async def test_tool_calling_integration():
    print("\n--- 6. Tool Calling Integration ---")
    settings = Settings()
    registry = create_default_registry(".")
    adapter = LLMAdapter(
        api_key=settings.ai_api_key,
        model=settings.ai_model,
        base_url=settings.ai_base_url
    )
    
    print(f"Using model: {adapter.model}")
    tools_schemas = registry.get_openai_schemas()
    
    messages = [
        ChatMessage(role="system", content="You are a helpful assistant. Only call one tool and wait for results."),
        ChatMessage(role="user", content="List the files in the current directory.")
    ]
    
    try:
        response = await adapter.generate(messages, tools=tools_schemas)
        if response.tool_calls:
            tc = response.tool_calls[0]
            print(f"✅ Model requested tool: {tc.name} with args {tc.arguments}")
            
            # Execute tool
            tool_res = await registry.execute(tc.name, tc.arguments)
            print(f"✅ Tool execution success: {tool_res.success}")
            print(f"Tool output snippet: {tool_res.output[:100]}...")
        else:
            print("❌ Model did not request any tools. Response:")
            print(response.content)
    except Exception as e:
        print(f"❌ Error during LLM generation: {e}")

async def main():
    await run_security_tests()
    await test_tool_calling_integration()

if __name__ == "__main__":
    asyncio.run(main())
