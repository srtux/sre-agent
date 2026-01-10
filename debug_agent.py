import asyncio
import logging
from gcp_observability.agent import gcp_observability

logging.basicConfig(level=logging.INFO)

async def main():
    print("Initializing agent...")
    agent = gcp_observability
    
    prompt = "Can you check the CPU usage for calculation-service and see if there are any anomalies?"
    print(f"Sending prompt: {prompt}")
    
    try:
        print("Response stream:")
        async for chunk in agent.run_async(prompt):
            print(chunk)
            # Check if chunk has tool calls
            # Usually chunk is a string or an object with delta
    except Exception as e:
        print(f"Agent execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
