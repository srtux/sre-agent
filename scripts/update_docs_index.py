#!/usr/bin/env python3
"""Auto SRE Documentation Index Generator.

This script parses all markdown files in the `docs/` directory, extracts their titles
(from the first H1 tag or `title:` frontmatter) or uses a fallback filename, and
rebuilds the DOCUMENTATION INDEX block inside `llm.txt`.

It also generates `repo_map.txt` representing the skeletal directory structure of the repository.
"""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
DOCS_DIR = ROOT_DIR / "docs"
LLM_TXT_PATH = ROOT_DIR / "llm.txt"
REPO_MAP_PATH = ROOT_DIR / "repo_map.txt"

# Directories to exclude from the repo map
EXCLUDE_DIRS = {
    ".git",
    ".github",
    "__pycache__",
    "node_modules",
    ".dart_tool",
    "build",
    "dist",
    ".mypy_cache",
    ".ruff_cache",
    "venv",
    ".venv",
    ".pytest_cache",
    ".gemini",
}


def extract_title(file_path: Path) -> str:
    """Extract the title of a markdown document."""
    try:
        content = file_path.read_text(encoding="utf-8")

        # Try YAML frontmatter
        title_match = re.search(r"^title:\s*(.*)$", content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()

        # Try first H1
        h1_match = re.search(r"^#\s+(.*)$", content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()

    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")

    # Fallback to filename
    return file_path.stem.replace("_", " ").title()


def generate_docs_index() -> str:
    """Generate the structured documentation index text."""
    index_lines = []

    # 1. Base files in docs/
    base_files = sorted(
        [f for f in DOCS_DIR.iterdir() if f.is_file() and f.suffix == ".md"]
    )
    for f in base_files:
        title = extract_title(f)
        # Fix lengths for alignment
        title = title[:52] + "..." if len(title) > 52 else title
        index_lines.append(f"  {f.name:<25} <- {title}")

    # 2. Subdirectories
    subdirs = sorted(
        [d for d in DOCS_DIR.iterdir() if d.is_dir() and d.name not in EXCLUDE_DIRS]
    )
    for d in subdirs:
        index_lines.append(f"  {d.name}/")
        files = sorted([f for f in d.iterdir() if f.is_file() and f.suffix == ".md"])
        for f in files:
            title = extract_title(f)
            title = title[:50] + "..." if len(title) > 50 else title
            index_lines.append(f"    {f.name:<23} <- {title}")

    return "\n".join(index_lines)


def update_llm_txt(index_content: str):
    """Inject the new index into llm.txt."""
    if not LLM_TXT_PATH.exists():
        print(f"Error: {LLM_TXT_PATH} not found.")
        return

    content = LLM_TXT_PATH.read_text(encoding="utf-8")

    # We look for the standard LLM.txt structure markers
    start_marker = "docs/"
    end_marker = "```"

    # Simple regex replacement for the block
    re.compile(
        rf"(^  {start_marker}\n)(.*?)(\n  [^\s].*?|\n{end_marker})",
        re.DOTALL | re.MULTILINE,
    )

    # If the block isn't cleanly found, let's just do a specific string replace
    # We will search for the first occurrence of "docs/\n" under "## DOCUMENTATION INDEX"
    marker_search = re.search(
        r"## DOCUMENTATION INDEX.*?```.*?docs/\n(.*?)```", content, re.DOTALL
    )

    if marker_search:
        old_index = marker_search.group(1)
        # Note: the new index does not contain the "docs/\n" header, it contains its contents and other dirs
        # We need to format the new content to match the indentation of the old block
        formatted_index = "\n" + index_content + "\n"
        new_content = content.replace(old_index, formatted_index)
        LLM_TXT_PATH.write_text(new_content, encoding="utf-8")
        print("Successfully updated llm.txt")
    else:
        print("Error: Could not find DOCUMENTATION INDEX block in llm.txt to replace.")


def generate_repo_map():
    """Generate a high-level repository map using tree structure."""

    def walk_tree(dir_path: Path, prefix: str = "") -> list:
        lines = []
        try:
            # Sort files and directories
            items = sorted(
                [
                    x
                    for x in dir_path.iterdir()
                    if x.name not in EXCLUDE_DIRS and not x.name.startswith(".")
                ],
                key=lambda x: (not x.is_dir(), x.name.lower()),
            )

            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                connector = "└── " if is_last else "├── "

                # Check if it's a directory with contents we want to expand
                if item.is_dir():
                    # Only go 3 levels deep from root
                    depth = len(item.relative_to(ROOT_DIR).parts)
                    if depth <= 3:
                        lines.append(f"{prefix}{connector}{item.name}/")
                        extension = "    " if is_last else "│   "
                        lines.extend(walk_tree(item, prefix + extension))
                    else:
                        lines.append(f"{prefix}{connector}{item.name}/ ...")
                else:
                    lines.append(f"{prefix}{connector}{item.name}")

        except PermissionError:
            pass

        return lines

    tree_lines = [f"Repo Map: {ROOT_DIR.name}/", ""]
    tree_lines.extend(walk_tree(ROOT_DIR))

    REPO_MAP_PATH.write_text("\n".join(tree_lines) + "\n", encoding="utf-8")
    print(f"Successfully generated {REPO_MAP_PATH.name}")


if __name__ == "__main__":
    print("Generating Documentation Index...")
    index_text = generate_docs_index()
    update_llm_txt(index_text)

    print("Generating Repository Map...")
    generate_repo_map()
    print("Done.")
