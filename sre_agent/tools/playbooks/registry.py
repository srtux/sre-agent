"""Playbook Registry for managing and searching troubleshooting playbooks."""

import logging
from typing import Any

from .schemas import (
    Playbook,
    PlaybookCategory,
    PlaybookSearchResult,
    PlaybookSeverity,
    TroubleshootingIssue,
)

logger = logging.getLogger(__name__)

# Singleton registry instance
_registry: "PlaybookRegistry | None" = None


def get_playbook_registry() -> "PlaybookRegistry":
    """Get the singleton playbook registry instance."""
    global _registry
    if _registry is None:
        _registry = PlaybookRegistry()
        _registry.load_all_playbooks()
    return _registry


class PlaybookRegistry:
    """Registry for managing GCP troubleshooting playbooks."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._playbooks: dict[str, Playbook] = {}
        self._by_category: dict[PlaybookCategory, list[str]] = {
            cat: [] for cat in PlaybookCategory
        }
        self._by_service: dict[str, str] = {}  # service_name -> playbook_id

    def register(self, playbook: Playbook) -> None:
        """Register a playbook in the registry."""
        self._playbooks[playbook.playbook_id] = playbook
        self._by_category[playbook.category].append(playbook.playbook_id)
        self._by_service[playbook.service_name.lower()] = playbook.playbook_id
        logger.debug(f"Registered playbook: {playbook.playbook_id}")

    def get(self, playbook_id: str) -> Playbook | None:
        """Get a playbook by ID."""
        return self._playbooks.get(playbook_id)

    def get_by_service(self, service_name: str) -> Playbook | None:
        """Get a playbook by service name."""
        playbook_id = self._by_service.get(service_name.lower())
        if playbook_id:
            return self._playbooks.get(playbook_id)
        return None

    def get_by_category(self, category: PlaybookCategory) -> list[Playbook]:
        """Get all playbooks in a category."""
        return [
            self._playbooks[pid]
            for pid in self._by_category.get(category, [])
            if pid in self._playbooks
        ]

    def list_all(self) -> list[Playbook]:
        """List all registered playbooks."""
        return list(self._playbooks.values())

    def search(
        self,
        query: str,
        category: PlaybookCategory | None = None,
        severity: PlaybookSeverity | None = None,
        limit: int = 10,
    ) -> list[PlaybookSearchResult]:
        """Search playbooks by query text.

        Args:
            query: Search text to match against playbooks and issues.
            category: Optional category filter.
            severity: Optional severity filter.
            limit: Maximum number of results.

        Returns:
            List of search results sorted by relevance.
        """
        results: list[PlaybookSearchResult] = []
        query_lower = query.lower()
        query_terms = query_lower.split()

        for playbook in self._playbooks.values():
            # Apply category filter
            if category and playbook.category != category:
                continue

            # Check playbook-level matches
            playbook_score = self._calculate_match_score(
                query_terms,
                [
                    playbook.service_name,
                    playbook.display_name,
                    playbook.description,
                ],
            )

            if playbook_score > 0:
                results.append(
                    PlaybookSearchResult(
                        playbook_id=playbook.playbook_id,
                        service_name=playbook.service_name,
                        relevance_score=min(playbook_score, 1.0),
                        match_reason=f"Matched service: {playbook.display_name}",
                    )
                )

            # Check issue-level matches
            for issue in playbook.issues:
                # Apply severity filter
                if severity and issue.severity != severity:
                    continue

                issue_score = self._calculate_match_score(
                    query_terms,
                    [
                        issue.title,
                        issue.description,
                        *issue.symptoms,
                        *issue.root_causes,
                        *issue.error_codes,
                    ],
                )

                if issue_score > 0:
                    results.append(
                        PlaybookSearchResult(
                            playbook_id=playbook.playbook_id,
                            service_name=playbook.service_name,
                            issue_id=issue.issue_id,
                            issue_title=issue.title,
                            relevance_score=min(issue_score, 1.0),
                            match_reason=f"Matched issue: {issue.title}",
                        )
                    )

        # Sort by relevance and limit
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]

    def _calculate_match_score(self, query_terms: list[str], texts: list[str]) -> float:
        """Calculate a simple relevance score based on term matches."""
        if not query_terms or not texts:
            return 0.0

        combined_text = " ".join(t.lower() for t in texts if t)
        matched_terms = sum(1 for term in query_terms if term in combined_text)

        return matched_terms / len(query_terms) if query_terms else 0.0

    def get_issue(self, playbook_id: str, issue_id: str) -> TroubleshootingIssue | None:
        """Get a specific issue from a playbook."""
        playbook = self.get(playbook_id)
        if not playbook:
            return None

        for issue in playbook.issues:
            if issue.issue_id == issue_id:
                return issue
        return None

    def get_diagnostic_steps_for_symptom(
        self, symptom: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Find diagnostic steps matching a symptom description.

        Args:
            symptom: Description of the observed symptom.
            limit: Maximum number of results.

        Returns:
            List of dicts with playbook, issue, and diagnostic steps.
        """
        results: list[dict[str, Any]] = []
        symptom_lower = symptom.lower()
        symptom_terms = symptom_lower.split()

        for playbook in self._playbooks.values():
            for issue in playbook.issues:
                # Check if any symptoms match
                for issue_symptom in issue.symptoms:
                    score = self._calculate_match_score(symptom_terms, [issue_symptom])
                    if score > 0.3:  # Threshold for relevance
                        results.append(
                            {
                                "playbook_id": playbook.playbook_id,
                                "service_name": playbook.service_name,
                                "issue_id": issue.issue_id,
                                "issue_title": issue.title,
                                "matched_symptom": issue_symptom,
                                "severity": issue.severity.value,
                                "diagnostic_steps": [
                                    step.model_dump() for step in issue.diagnostic_steps
                                ],
                                "relevance_score": score,
                            }
                        )
                        break  # Only add each issue once

        # Sort by relevance and limit
        results.sort(key=lambda r: r["relevance_score"], reverse=True)
        return results[:limit]

    def load_all_playbooks(self) -> None:
        """Load all built-in playbooks."""
        from . import bigquery, cloud_run, cloud_sql, gce, gke, pubsub, self_healing

        # Register playbooks from each module
        for module in [gke, cloud_run, cloud_sql, gce, bigquery, pubsub, self_healing]:
            if hasattr(module, "get_playbook"):
                playbook = module.get_playbook()
                self.register(playbook)

        logger.info(f"Loaded {len(self._playbooks)} playbooks")
