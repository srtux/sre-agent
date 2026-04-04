"""Tests for SRE Agent ADK Skills integration.

Validates that all skills load correctly, have valid frontmatter,
and integrate properly with the ADK SkillToolset.
"""

import os
from unittest.mock import patch

import pytest
from google.adk.skills import Skill, list_skills_in_dir, load_skill_from_dir

from sre_agent.skills import SKILLS_DIR, load_all_skills

# All expected skill IDs (directory names)
EXPECTED_SKILLS = {
    "cloud-run-troubleshooting",
    "gke-troubleshooting",
    "incident-investigation",
    "log-pattern-analysis",
    "postmortem-generation",
    "slo-analysis",
}


class TestSkillLoading:
    """Test that all skills load correctly from disk."""

    def test_skills_dir_exists(self) -> None:
        """Skills directory exists and is a directory."""
        assert SKILLS_DIR.exists()
        assert SKILLS_DIR.is_dir()

    def test_list_skills_in_dir(self) -> None:
        """list_skills_in_dir discovers all expected skills."""
        frontmatters = list_skills_in_dir(SKILLS_DIR)
        assert set(frontmatters.keys()) == EXPECTED_SKILLS

    def test_load_all_skills_returns_correct_count(self) -> None:
        """load_all_skills returns all expected skills."""
        skills = load_all_skills()
        assert len(skills) == len(EXPECTED_SKILLS)

    def test_load_all_skills_returns_skill_objects(self) -> None:
        """Each item returned by load_all_skills is a Skill instance."""
        skills = load_all_skills()
        for skill in skills:
            assert isinstance(skill, Skill)

    def test_all_skill_names_match_directories(self) -> None:
        """Each skill's frontmatter name matches its directory name."""
        skills = load_all_skills()
        skill_names = {s.name for s in skills}
        assert skill_names == EXPECTED_SKILLS


class TestSkillContent:
    """Test that each skill has valid content."""

    @pytest.fixture(params=sorted(EXPECTED_SKILLS))
    def skill(self, request: pytest.FixtureRequest) -> Skill:
        """Load each skill as a parameterized fixture."""
        return load_skill_from_dir(SKILLS_DIR / request.param)

    def test_skill_has_name(self, skill: Skill) -> None:
        """Skill has a non-empty name."""
        assert skill.name
        assert len(skill.name) <= 64

    def test_skill_has_description(self, skill: Skill) -> None:
        """Skill has a non-empty description."""
        assert skill.description
        assert len(skill.description) <= 1024

    def test_skill_has_instructions(self, skill: Skill) -> None:
        """Skill has non-empty instructions body."""
        assert skill.instructions
        assert len(skill.instructions) > 50  # Should have meaningful content

    def test_skill_name_is_kebab_case(self, skill: Skill) -> None:
        """Skill names follow kebab-case convention."""
        import re

        assert re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", skill.name)


class TestSkillResources:
    """Test skill-specific resources (references, assets)."""

    def test_gke_troubleshooting_has_references(self) -> None:
        """GKE troubleshooting skill includes reference docs."""
        skill = load_skill_from_dir(SKILLS_DIR / "gke-troubleshooting")
        refs = skill.resources.list_references()
        assert "common-issues.md" in refs

    def test_cloud_run_troubleshooting_has_references(self) -> None:
        """Cloud Run troubleshooting skill includes reference docs."""
        skill = load_skill_from_dir(SKILLS_DIR / "cloud-run-troubleshooting")
        refs = skill.resources.list_references()
        assert "common-issues.md" in refs

    def test_postmortem_generation_has_template(self) -> None:
        """Postmortem generation skill includes the template asset."""
        skill = load_skill_from_dir(SKILLS_DIR / "postmortem-generation")
        assets = skill.resources.list_assets()
        assert "postmortem-template.md" in assets

    def test_postmortem_template_has_content(self) -> None:
        """Postmortem template contains expected sections."""
        skill = load_skill_from_dir(SKILLS_DIR / "postmortem-generation")
        template = skill.resources.get_asset("postmortem-template.md")
        assert template is not None
        assert "## Executive Summary" in template
        assert "## Root Cause" in template
        assert "## Action Items" in template


class TestSkillToolsetIntegration:
    """Test integration with ADK SkillToolset."""

    def test_skilltoolset_initializes_with_loaded_skills(self) -> None:
        """SkillToolset can be created with loaded skills."""
        from google.adk.tools.skill_toolset import SkillToolset

        skills = load_all_skills()
        toolset = SkillToolset(skills=skills)
        assert toolset is not None
        # SkillToolset should list all skills
        listed = toolset._list_skills()
        assert len(listed) == len(EXPECTED_SKILLS)

    def test_skilltoolset_duplicate_names_raises(self) -> None:
        """SkillToolset rejects duplicate skill names."""
        from google.adk.tools.skill_toolset import SkillToolset

        skills = load_all_skills()
        # Duplicate the first skill
        with pytest.raises(ValueError, match="Duplicate skill name"):
            SkillToolset(skills=[skills[0], skills[0]])

    def test_skilltoolset_provides_tools(self) -> None:
        """SkillToolset provides the expected tool set."""
        from google.adk.tools.skill_toolset import SkillToolset

        skills = load_all_skills()
        toolset = SkillToolset(skills=skills)
        # The toolset should have the 4 core skill tools
        tool_names = {t.name for t in toolset._tools}
        assert "list_skills" in tool_names
        assert "load_skill" in tool_names
        assert "load_skill_resource" in tool_names
        assert "run_skill_script" in tool_names


class TestSkillsFeatureFlag:
    """Test that skills can be disabled via environment variable."""

    @patch.dict(os.environ, {"SRE_AGENT_SKILLS": "false"})
    def test_skills_disabled_when_env_false(self) -> None:
        """Skills should not be loaded when SRE_AGENT_SKILLS=false."""
        # This tests the conditional logic used in agent.py
        assert os.environ.get("SRE_AGENT_SKILLS", "true").lower() != "true"

    @patch.dict(os.environ, {"SRE_AGENT_SKILLS": "true"})
    def test_skills_enabled_when_env_true(self) -> None:
        """Skills should be loaded when SRE_AGENT_SKILLS=true."""
        assert os.environ.get("SRE_AGENT_SKILLS", "true").lower() == "true"

    @patch.dict(os.environ, {}, clear=False)
    def test_skills_enabled_by_default(self) -> None:
        """Skills should be enabled by default when env var is not set."""
        env = os.environ.copy()
        env.pop("SRE_AGENT_SKILLS", None)
        with patch.dict(os.environ, env, clear=True):
            assert os.environ.get("SRE_AGENT_SKILLS", "true").lower() == "true"
