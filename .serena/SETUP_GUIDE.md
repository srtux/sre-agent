# Setup Guide for SRE Agent

Serena has been successfully set up and indexed for this project.

## Project Details
- **Project Name**: `sre-agent`
- **Languages**: Python, Dart (Flutter)
- **Status**: Indexed (452 files)
- **Health Check**: Passed ✅

## How to Use

### 1. With Claude Desktop (Recommended)
Add Serena as an MCP server to your Claude Desktop configuration.

**Config Location**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Add this entry**:
```json
{
  "mcpServers": {
    "serena": {
      "command": "/Users/user/.local/bin/serena",
      "args": ["start-mcp-server", "--project-from-cwd"]
    }
  }
}
```

### 2. With Claude Code (CLI)
You can add Serena directly to your Claude Code CLI to enable advanced code search and project context.

**Run this command**:
```bash
claude mcp add serena -- /Users/user/.local/bin/serena start-mcp-server --context=claude-code --project-from-cwd
```

This will create or update a `.claude.json` file in your project root with the Serena MCP configuration.

### 3. CLI Usage
You can use the `serena` CLI for various tasks:

- **Re-index the project**:
  ```bash
  serena project index .
  ```
- **Run Health Check**:
  ```bash
  serena project health-check .
  ```
- **Edit Global Config**:
  ```bash
  serena config edit
  ```

## OpenSpec Integration

This project is configured with **OpenSpec** for structured task and change management.

### OpenSpec with Claude Code
Claude Code is equipped with specialized OpenSpec skills and slash commands to guide you through the developer workflow.

**Available Slash Commands**:
- `/opsx-new` – Start a new change or feature.
- `/opsx-apply` – Implement tasks from an existing change.
- `/opsx-continue` – Progress to the next artifact/step in the workflow.
- `/opsx-verify` – Verify that implementation matches the change specs.
- `/opsx-explore` – Investigate problems or explore high-level ideas.

**CLI Tooling**:
The `openspec` CLI is available globally for manual operations:
```bash
# Check status of current change
openspec status

# List available specifications
openspec spec list
```

## Key Features in this Project
- **Symbol Search**: Quickly find functions, classes, and variables across Python and Dart.
- **Memories**: Serena stores project-specific knowledge in `.serena/memories/`. These help future agents (like this one) understand the architecture and patterns of SRE Agent.
- **Language Servers**: Serena automatically starts language servers for Python and Dart to provide deep code understanding.

## Claude Code Agent Teams (Experimental)

This project is configured to use **Agent Teams**, allowing you to orchestrate multiple Claude sessions to work together on complex tasks.

### Status
- **Experimental Flag**: Enabled in `.claude/settings.json`.
- **Display Mode**: `auto` (currently using `split-pane` via `tmux`).

### How to Use
To start a team, simply ask Claude to create one in your prompt:
```bash
# Example prompt:
"I want to refactor the core engine. Create a team with an architect, a tester, and a developer to handle this in parallel."
```

**Controls**:
- **Shift + Up/Down**: Switch between teammate sessions.
- **Ctrl + T**: Toggle the shared task list.
- **Escape**: Interrupt a teammate's turn.
- **Enter**: Deep dive into a teammate's session.
- **Cleanup**: "Clean up the team" to shut down all teammates.
