"""Storage Service for SRE Agent.

Provides persistent storage for user preferences and state.
Uses local file storage in development and Firestore in Cloud Run.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract storage backend."""

    @abstractmethod
    async def get(self, collection: str, key: str) -> dict[str, Any] | None:
        """Get a document by key."""
        pass

    @abstractmethod
    async def set(self, collection: str, key: str, data: dict[str, Any]) -> None:
        """Set a document by key."""
        pass

    @abstractmethod
    async def delete(self, collection: str, key: str) -> bool:
        """Delete a document by key."""
        pass

    @abstractmethod
    async def list(self, collection: str, limit: int = 100) -> list[dict[str, Any]]:
        """List all documents in a collection."""
        pass

    @abstractmethod
    async def query(
        self,
        collection: str,
        field: str,
        value: Any,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query documents by field value."""
        pass


class LocalFileStorage(StorageBackend):
    """Local file-based storage for development."""

    def __init__(self, base_path: str = ".sre_agent_data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalFileStorage initialized at {self.base_path}")

    def _get_collection_path(self, collection: str) -> Path:
        """Get path for a collection."""
        collection_path = self.base_path / collection
        collection_path.mkdir(parents=True, exist_ok=True)
        return collection_path

    def _get_file_path(self, collection: str, key: str) -> Path:
        """Get path for a specific document."""
        return self._get_collection_path(collection) / f"{key}.json"

    async def get(self, collection: str, key: str) -> dict[str, Any] | None:
        """Get a document by key."""
        file_path = self._get_file_path(collection, key)
        if not file_path.exists():
            return None
        try:
            with open(file_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None

    async def set(self, collection: str, key: str, data: dict[str, Any]) -> None:
        """Set a document by key."""
        file_path = self._get_file_path(collection, key)
        data["_id"] = key
        data["_updated_at"] = datetime.utcnow().isoformat()
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error writing {file_path}: {e}")
            raise

    async def delete(self, collection: str, key: str) -> bool:
        """Delete a document by key."""
        file_path = self._get_file_path(collection, key)
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")
                return False
        return False

    async def list(self, collection: str, limit: int = 100) -> list[dict[str, Any]]:
        """List all documents in a collection."""
        collection_path = self._get_collection_path(collection)
        documents = []
        for file_path in sorted(
            collection_path.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]:
            try:
                with open(file_path) as f:
                    doc = json.load(f)
                    doc["_id"] = file_path.stem
                    documents.append(doc)
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
        return documents

    async def query(
        self,
        collection: str,
        field: str,
        value: Any,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query documents by field value."""
        all_docs = await self.list(collection, limit=1000)
        results = []
        for doc in all_docs:
            if doc.get(field) == value:
                results.append(doc)
                if len(results) >= limit:
                    break
        return results


class FirestoreStorage(StorageBackend):
    """Firestore-based storage for Cloud Run deployments."""

    def __init__(self, project_id: str | None = None):
        try:
            from google.cloud import firestore
        except ImportError:
            raise ImportError(
                "google-cloud-firestore is required for Firestore storage. "
                "Install it with: pip install google-cloud-firestore"
            )

        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.db = firestore.AsyncClient(project=self.project_id)
        logger.info(f"FirestoreStorage initialized for project {self.project_id}")

    async def get(self, collection: str, key: str) -> dict[str, Any] | None:
        """Get a document by key."""
        try:
            doc_ref = self.db.collection(collection).document(key)
            doc = await doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                if data:
                    data["_id"] = key
                return data
            return None
        except Exception as e:
            logger.error(f"Firestore get error: {e}")
            return None

    async def set(self, collection: str, key: str, data: dict[str, Any]) -> None:
        """Set a document by key."""
        try:
            from google.cloud import firestore

            data["_id"] = key
            data["_updated_at"] = firestore.SERVER_TIMESTAMP
            doc_ref = self.db.collection(collection).document(key)
            await doc_ref.set(data)
        except Exception as e:
            logger.error(f"Firestore set error: {e}")
            raise

    async def delete(self, collection: str, key: str) -> bool:
        """Delete a document by key."""
        try:
            doc_ref = self.db.collection(collection).document(key)
            await doc_ref.delete()
            return True
        except Exception as e:
            logger.error(f"Firestore delete error: {e}")
            return False

    async def list(self, collection: str, limit: int = 100) -> list[dict[str, Any]]:
        """List all documents in a collection."""
        try:
            docs = (
                self.db.collection(collection)
                .order_by("_updated_at", direction="DESCENDING")
                .limit(limit)
            )
            documents = []
            async for doc in docs.stream():
                data = doc.to_dict()
                if data:
                    data["_id"] = doc.id
                    documents.append(data)
            return documents
        except Exception as e:
            logger.error(f"Firestore list error: {e}")
            return []

    async def query(
        self,
        collection: str,
        field: str,
        value: Any,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query documents by field value."""
        try:
            docs = (
                self.db.collection(collection)
                .where(field, "==", value)
                .limit(limit)
            )
            documents = []
            async for doc in docs.stream():
                data = doc.to_dict()
                if data:
                    data["_id"] = doc.id
                    documents.append(data)
            return documents
        except Exception as e:
            logger.error(f"Firestore query error: {e}")
            return []


class StorageService:
    """High-level storage service for user preferences and state."""

    # Collection names
    COLLECTION_PREFERENCES = "user_preferences"
    COLLECTION_SESSIONS = "sessions"
    COLLECTION_SESSION_HISTORY = "session_history"

    # Preference keys
    PREF_SELECTED_PROJECT = "selected_project"
    PREF_TOOL_CONFIG = "tool_config"

    def __init__(self, backend: StorageBackend):
        self.backend = backend

    # =========================================================================
    # User Preferences
    # =========================================================================

    async def get_user_preference(
        self, user_id: str, key: str
    ) -> dict[str, Any] | None:
        """Get a user preference."""
        doc = await self.backend.get(
            self.COLLECTION_PREFERENCES,
            f"{user_id}_{key}",
        )
        return doc

    async def set_user_preference(
        self, user_id: str, key: str, value: dict[str, Any]
    ) -> None:
        """Set a user preference."""
        await self.backend.set(
            self.COLLECTION_PREFERENCES,
            f"{user_id}_{key}",
            {"user_id": user_id, "key": key, "value": value},
        )

    async def delete_user_preference(self, user_id: str, key: str) -> bool:
        """Delete a user preference."""
        return await self.backend.delete(
            self.COLLECTION_PREFERENCES,
            f"{user_id}_{key}",
        )

    # =========================================================================
    # Project Selection
    # =========================================================================

    async def get_selected_project(self, user_id: str = "default") -> str | None:
        """Get the selected project for a user."""
        pref = await self.get_user_preference(user_id, self.PREF_SELECTED_PROJECT)
        if pref and "value" in pref:
            return pref["value"].get("project_id")
        return None

    async def set_selected_project(
        self, project_id: str, user_id: str = "default"
    ) -> None:
        """Set the selected project for a user."""
        await self.set_user_preference(
            user_id,
            self.PREF_SELECTED_PROJECT,
            {"project_id": project_id},
        )

    # =========================================================================
    # Tool Configuration
    # =========================================================================

    async def get_tool_config(
        self, user_id: str = "default"
    ) -> dict[str, bool] | None:
        """Get tool configuration for a user."""
        pref = await self.get_user_preference(user_id, self.PREF_TOOL_CONFIG)
        if pref and "value" in pref:
            return pref["value"].get("enabled_tools")
        return None

    async def set_tool_config(
        self, enabled_tools: dict[str, bool], user_id: str = "default"
    ) -> None:
        """Set tool configuration for a user."""
        await self.set_user_preference(
            user_id,
            self.PREF_TOOL_CONFIG,
            {"enabled_tools": enabled_tools},
        )


# ============================================================================
# Singleton Access
# ============================================================================

_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get the singleton StorageService instance.

    Uses Firestore if running in Cloud Run (K_SERVICE env var is set),
    otherwise uses local file storage.
    """
    global _storage_service
    if _storage_service is None:
        # Detect if running in Cloud Run
        is_cloud_run = os.getenv("K_SERVICE") is not None
        use_firestore = os.getenv("USE_FIRESTORE", "").lower() == "true"

        if is_cloud_run or use_firestore:
            try:
                backend = FirestoreStorage()
                logger.info("Using Firestore storage backend")
            except Exception as e:
                logger.warning(f"Failed to initialize Firestore, falling back to local: {e}")
                backend = LocalFileStorage()
        else:
            backend = LocalFileStorage()
            logger.info("Using local file storage backend")

        _storage_service = StorageService(backend)

    return _storage_service
