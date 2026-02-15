# AutoSRE Help Center: Architecture & DaC Guide

## Strategic Objective
The AutoSRE Help Center is designed to provide immediate, context-aware guidance to SREs during high-pressure incidents. It follows a **Documentation-as-Code (DaC)** model, ensuring that documentation is versioned, tested, and deployed alongside the codebase.

---

## System Architecture

The help system is decoupled into three distinct layers:

### 1. Data Layer (Docs Repository)
- **Path**: `docs/help/`
- **Structure**:
  - `manifest.json`: The central registry of all help topics, including IDs, titles, icons, and categories.
  - `content/`: A folder containing Markdown files for each topic.
- **Why**: Allows non-developers to contribute documentation via Markdown without touching UI code.

### 2. Plumbing Layer (FastAPI Backend)
- **Router**: `sre_agent/api/routers/help.py`
- **Endpoints**:
  - `GET /api/help/manifest`: Lazily loads and returns the `manifest.json`.
  - `GET /api/help/content/{id}`: Streams the raw Markdown content for a specific topic.
- **Security**: Implements path sanitization to prevent directory traversal attacks.

### 3. UI Layer (Flutter Frontend)
- **Service**: `HelpService` (`lib/services/help_service.dart`)
- **Page**: `HelpPage` (`lib/pages/help_page.dart`)
- **Widgets** (`lib/widgets/help/`):
  - Help card components for expandable topic display.
  - Markdown rendering with theme-aware styling.
  - Search and category filtering.

---

## The DaC Workflow: Adding a New Topic

To add a new help topic, follow these steps:

1.  **Create Markdown**: Add a new file in `docs/help/content/your_topic.md`. Use high-quality, actionable language.
2.  **Register in Manifest**: Add an entry to `docs/help/manifest.json`:
    ```json
    {
      "id": "your_topic",
      "title": "Your Feature",
      "description": "Short summary for the card.",
      "icon": "your_icon_name",
      "categories": ["Category"],
      "content_file": "your_topic.md"
    }
    ```
3.  **Verify Locally**: Run `uv run poe dev` and check the "Help" page in the dashboard.
4.  **Add Regression Test**: Ensure your new topic is visible in the Flutter test suite (or rely on existing unit tests if no new logic was added).

---

## Mandatory Policy: The Documentation Gate

**Rule**: Every new feature or functional change **MUST** include updates to:
1.  **Internal Docs**: Update relevant files in `docs/architecture/` or `docs/reference/`.
2.  **Public Help Center**: Add or update topics in `docs/help/` to explain the feature to the end-user.

*Failure to provide documentation will block the PR.*
