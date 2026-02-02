### Powered by Gemini
AutoSRE is primarily powered by **Gemini 1.5 Pro**, Google's high-performance multimodal model.

- **Long Context**: The agent leverages the 2M+ token context window to ingest massive trace logs and deployment histories simultaneously.
- **Reasoning**: It uses specialized SRE-tuned prompts to follow the "Detective Methodology" rather than just predicting text.
- **Safety**: We use the model's safety layers to ensure the agent doesn't perform destructive actions without confirmation.
