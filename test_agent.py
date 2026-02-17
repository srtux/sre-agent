import asyncio

from dotenv import load_dotenv

load_dotenv()

from sre_agent.services.agent_engine_client import AgentEngineClient, AgentEngineConfig


async def run():
    config = AgentEngineConfig(
        project_id="summitt-gcp", location="us-central1", agent_id="4168506966131343360"
    )
    client = AgentEngineClient(config)
    stream = client.stream_query(
        user_id="test@example.com",
        message="hi",
        access_token="fake_token_to_bypass",  # Test
        project_id="summitt-gcp",
        session_id=None,  # Let it create one
    )
    async for event in stream:
        print("EVENT:", event)


if __name__ == "__main__":
    asyncio.run(run())
