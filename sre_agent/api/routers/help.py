import json
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/help", tags=["help"])

# Base directory for documentation
# This assumes the file is in sre_agent/api/routers/help.py
_CURRENT_FILE = os.path.abspath(__file__)
_ROUTERS_DIR = os.path.dirname(_CURRENT_FILE)
_API_DIR = os.path.dirname(_ROUTERS_DIR)
_SRE_AGENT_DIR = os.path.dirname(_API_DIR)
_ROOT_DIR = os.path.dirname(_SRE_AGENT_DIR)

DOCS_DIR = os.path.join(_ROOT_DIR, "docs", "help")
# print(f"DEBUG: DOCS_DIR is {DOCS_DIR}")


@router.get("/manifest")
async def get_help_manifest() -> Any:
    """Retrieve the manifest of available help topics."""
    manifest_path = os.path.join(DOCS_DIR, "manifest.json")
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="Help manifest not found")

    with open(manifest_path) as f:
        manifest = json.load(f)
    return manifest


@router.get("/content/{content_id}")
async def get_help_content(content_id: str) -> PlainTextResponse:
    """Retrieve the markdown content for a specific help topic."""
    # Prevent directory traversal
    safe_id = content_id.replace("..", "").replace("/", "").replace("\\", "")
    if safe_id != content_id:
        raise HTTPException(status_code=400, detail="Invalid content ID")

    # The manifest maps content_id to filenames, but for simplicity,
    # we'll check common extensions if id doesn't match exactly.
    content_path = os.path.join(DOCS_DIR, "content", f"{safe_id}.md")

    if not os.path.exists(content_path):
        # Check if it was passed with .md already
        if content_id.endswith(".md"):
            content_path = os.path.join(DOCS_DIR, "content", safe_id)

        if not os.path.exists(content_path):
            raise HTTPException(
                status_code=404, detail=f"Content for {content_id} not found"
            )

    with open(content_path, encoding="utf-8") as f:
        content = f.read()

    return PlainTextResponse(content)
