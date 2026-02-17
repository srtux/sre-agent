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
    # Step 0: Input validation for safety and to satisfy security tests
    if ".." in content_id or "/" in content_id or "\\" in content_id:
        raise HTTPException(status_code=400, detail="Invalid content ID")

    # Normalize: strip .md if present (handles legacy links or explicit extensions)
    if content_id.endswith(".md"):
        content_id = content_id[:-3]

    # Step 1: Load manifest to use as an allow-list
    manifest = await get_help_manifest()

    # Step 2: Find the matching topic
    topic = next((t for t in manifest if t.get("id") == content_id), None)
    if not topic:
        raise HTTPException(status_code=404, detail="Help topic not found")

    content_file = topic.get("content_file")
    if not content_file or not re.match(r"^[a-zA-Z0-9_\-]+\.md$", content_file):
        raise HTTPException(status_code=500, detail="Invalid manifest configuration")

    # Step 3: Construct the path using the filename from the manifest (not from user input)
    base_content_dir = _DOCS_RESOLVED / "content"
    content_path = (base_content_dir / content_file).resolve()

    # Step 4: Final safety check (even though content_file is from manifest)
    if not str(content_path).startswith(str(base_content_dir)):
        raise HTTPException(
            status_code=400, detail="Security violation: Invalid path access"
        )

    if not content_path.exists():
        raise HTTPException(status_code=404, detail="Help topic file not found")

    content = content_path.read_text(encoding="utf-8")
    return PlainTextResponse(content)
