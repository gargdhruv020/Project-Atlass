"""
Entitlement-Aware Cache for Project Atlas
Ensures cache keys explicitly incorporate client_id and the verified authorized report scope,
preventing cross-client information leakage or cache poisoning between different client subscriptions.
"""

import time
import hashlib
from typing import Optional, Set, Dict, Any
from threading import Lock

from app.schemas.chat import ChatResponse
from app.observability.logger import logger


class EntitlementCache:
    """
    Thread-safe, TTL-based response cache partitioned by client and authorized report scope.
    """

    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    @staticmethod
    def generate_cache_key(
        client_id: str,
        permitted_reports: Set[str],
        query: str,
        report_id: Optional[str] = None
    ) -> str:
        """
        Constructs a deterministic SHA-256 hash partitioned by:
        1. Calling client_id
        2. Sorted permitted report scope (from MySQL)
        3. Explicit target report_id (if scoped)
        4. Normalized query prompt
        """
        sorted_scope = ",".join(sorted(list(permitted_reports)))
        norm_query = query.strip().lower()
        target = (report_id or "*").upper()

        raw_key = f"client:{client_id}|scope:[{sorted_scope}]|target:{target}|q:{norm_query}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(
        self,
        client_id: str,
        permitted_reports: Set[str],
        query: str,
        report_id: Optional[str] = None
    ) -> Optional[ChatResponse]:
        """
        Retrieves cached ChatResponse if present and unexpired.
        Returns None if cache miss or expired.
        """
        key = self.generate_cache_key(client_id, permitted_reports, query, report_id)
        now = time.time()

        with self._lock:
            entry = self._cache.get(key)
            if entry and entry["expires_at"] > now:
                self.hits += 1
                logger.debug(f"[Cache] Hit for client '{client_id}', query '{query[:30]}...'")
                return entry["response"]
            
            if entry and entry["expires_at"] <= now:
                # Evict expired
                del self._cache[key]

            self.misses += 1
            return None

    def set(
        self,
        client_id: str,
        permitted_reports: Set[str],
        query: str,
        response: ChatResponse,
        report_id: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> str:
        """
        Caches ChatResponse for specified TTL (seconds).
        Returns the generated cache key.
        """
        key = self.generate_cache_key(client_id, permitted_reports, query, report_id)
        expires_at = time.time() + (ttl or self.default_ttl)

        with self._lock:
            self._cache[key] = {
                "response": response,
                "expires_at": expires_at,
                "client_id": client_id,
                "permitted_reports": sorted(list(permitted_reports))
            }
            logger.debug(f"[Cache] Stored entry for client '{client_id}', key '{key[:12]}...'")

        return key

    def clear(self) -> None:
        """Flushes entire cache."""
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> Dict[str, Any]:
        """Returns cache statistics."""
        with self._lock:
            now = time.time()
            active_entries = sum(1 for e in self._cache.values() if e["expires_at"] > now)
            return {
                "active_entries": active_entries,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(self.hits / max(1, self.hits + self.misses), 2)
            }


# Singleton entitlement cache
entitlement_cache = EntitlementCache()
