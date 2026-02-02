### Extending the Agent
Yes! AutoSRE is built on the **Model Context Protocol (MCP)** and can be extended easily.

- **Python Tools**: You can add new tools in `sre_agent/tools/`.
- **MCP Servers**: You can connect external MCP servers providing specialized data (e.g., GitHub, Slack, specific DBs).
- **Configuration**: Use the `.tool_config.json` file to enable or disable specific functionalities.

For developers: check out `docs/guides/development.md` for a full tutorial on adding new tools.
