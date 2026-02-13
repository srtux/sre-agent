import vertexai
from vertexai.preview import reasoning_engines

vertexai.init(project="summitt-gcp", location="us-central1")
engine = reasoning_engines.ReasoningEngine("4168506966131343360")
print(engine._gca_resource.spec.package_spec)
