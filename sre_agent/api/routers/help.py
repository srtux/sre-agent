import json
import os
import re
from pathlib import Path
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
_DOCS_RESOLVED = Path(DOCS_DIR).resolve()


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
    # Step 1: Strict Character Validation (Allow-list)
    # Only allow Alphanumeric, underscores, and dashes. No dots, slashes, or special chars.
    if not re.match(r"^[a-zA-Z0-9_\-]+$", content_id):
        raise HTTPException(status_code=400, detail="Invalid help topic ID")

    # Step 2: Ensure path is within the designated content directory
    base_content_dir = _DOCS_RESOLVED / "content"
    content_path = (base_content_dir / f"{content_id}.md").resolve()

    # Step 3: Verify the resolved path starts with the base content directory
    if not str(content_path).startswith(str(base_content_dir)):
        raise HTTPException(
            status_code=400, detail="Security violation: Invalid path access"
        )

    if not content_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Help topic '{content_id}' not found"
        )

    content = content_path.read_text(encoding="utf-8")
    return PlainTextResponse(content)
