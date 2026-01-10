import asyncio
import logging
from gcp_observability.agent import gcp_observability

logging.basicConfig(level=logging.INFO)

async def main():
    print("Initializing agent...")
    agent = gcp_observability
    
    prompt = "Can you check the CPU usage for calculation-service and see if there are any anomalies?"
    print(f"Sending prompt: {prompt}")
    
    from google.adk.runners import InMemoryRunner
    # from google.adk.invocation_context import InvocationContext
    
    print("Using InMemoryRunner...")
    runner = InMemoryRunner(agent=agent)
    import inspect
    print(f"runner.run_async signature: {inspect.signature(runner.run_async)}")
    
    # We need to create a Content object
    from google.adk.types import Content, Part
    
    content = Content(role="user", parts=[Part(text=prompt)])

    try:
        async for event in runner.run_async(
            user_id="test-user",
            session_id="test-session",
            new_message=content
        ):
            print(f"Event: {event}")
            if hasattr(event, "tool_usage"):
                print(f"Tool Usage: {event.tool_usage}")
            if hasattr(event, "message"):
                print(f"Message: {event.message}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Runner execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
