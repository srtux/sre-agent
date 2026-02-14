from google.adk.memory import VertexAiMemoryBankService

service = VertexAiMemoryBankService(
    project="221980738988",
    location="us-central1",
    agent_engine_id="projects/221980738988/locations/us-central1/reasoningEngines/4168506966131343360",
)
client = service._get_api_client()  # type: ignore
help(client.agent_engines.memories.create)
