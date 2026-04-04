"""ADK Skills for the SRE Agent.

Provides structured, discoverable skill definitions that guide the agent
through specialized SRE workflows (incident investigation, troubleshooting,
postmortem generation, etc.).

Skills are loaded from SKILL.md files in subdirectories and registered
with the ADK SkillToolset, which exposes them to the LLM at runtime.
"""

import logging
import pathlib

from google.adk.skills import Skill, list_skills_in_dir, load_skill_from_dir

logger = logging.getLogger(__name__)

SKILLS_DIR = pathlib.Path(__file__).parent


def load_all_skills() -> list[Skill]:
    """Load all valid skills from the skills directory.

    Returns:
        List of Skill objects loaded from subdirectories of ``SKILLS_DIR``.
        Invalid or malformed skills are logged and skipped.
    """
    frontmatters = list_skills_in_dir(SKILLS_DIR)
    skills: list[Skill] = []
    for skill_id in sorted(frontmatters):
        try:
            skill = load_skill_from_dir(SKILLS_DIR / skill_id)
            skills.append(skill)
            logger.debug("Loaded skill: %s", skill_id)
        except (FileNotFoundError, ValueError) as exc:
            logger.warning("Skipping invalid skill '%s': %s", skill_id, exc)
    logger.info("Loaded %d SRE skills", len(skills))
    return skills
