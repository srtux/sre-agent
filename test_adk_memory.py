import asyncio

from google.adk.memory import VertexAiMemoryBankService


async def main() -> None:
    """Run the Vertex AI Memory Bank Service test."""
    service = VertexAiMemoryBankService(
        project="221980738988",
        location="us-central1",
        agent_engine_id="projects/221980738988/locations/us-central1/reasoningEngines/4168506966131343360",
    )
    print(service._agent_engine_id)


asyncio.run(main())
