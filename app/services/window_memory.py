"""
Window Memory Service using Redis
Implements sliding window conversation memory, rate limiting, and semantic search caching.
"""

import os
import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
import redis

logger = logging.getLogger(__name__)

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
WINDOW_SIZE = int(os.getenv("WINDOW_MEMORY_SIZE", "5"))  # Number of messages to keep
WINDOW_TTL = int(os.getenv("WINDOW_MEMORY_TTL", "1800"))  # Time-to-live in seconds
SEARCH_CACHE_TTL = int(os.getenv("SEARCH_CACHE_TTL", "86400"))  # 24 hours for search cache


class WindowMemoryManager:
    """Manages conversation history using Redis with sliding window mechanism."""

    def __init__(self, redis_url: str = REDIS_URL):
        """Initialize Redis connection pool."""
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("✅ Redis connection established for Window Memory")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self.redis_client = None

    def _get_session_key(self, session_id: str) -> str:
        return f"window_memory:session:{session_id}"

    def _get_session_meta_key(self, session_id: str) -> str:
        return f"window_memory:meta:{session_id}"

    def _get_stats_key(self, session_id: str) -> str:
        return f"window_memory:stats:{session_id}"

    def add_message(self, session_id: str, message: str, role: str = "user", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add a message to the session's conversation window."""
        if not self.redis_client:
            logger.warning("Redis client not available, skipping message storage")
            return False

        try:
            session_key = self._get_session_key(session_id)
            timestamp = time.time()

            msg_obj = {
                "timestamp": timestamp,
                "datetime": datetime.now().isoformat(),
                "role": role,
                "message": message,
                "metadata": json.dumps(metadata or {}),
            }

            self.redis_client.rpush(session_key, json.dumps(msg_obj))
            self.redis_client.ltrim(session_key, -WINDOW_SIZE, -1)
            self.redis_client.expire(session_key, WINDOW_TTL)

            self._update_session_metadata(session_id, role)
            self._update_statistics(session_id, role)

            logger.debug(f"Added {role} message to session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding message to window memory: {e}")
            return False

    def get_conversation_window(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Retrieve conversation history for a session."""
        if not self.redis_client:
            return []

        try:
            session_key = self._get_session_key(session_id)
            limit = limit or WINDOW_SIZE

            messages_data = self.redis_client.lrange(session_key, -limit, -1)

            messages = []
            for msg_data in messages_data:
                try:
                    msg = json.loads(msg_data)
                    msg["metadata"] = json.loads(msg["metadata"])
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue

            logger.debug(f"Retrieved {len(messages)} messages from session {session_id}")
            return messages

        except Exception as e:
            logger.error(f"Error retrieving conversation window: {e}")
            return []

    def get_context_summary(self, session_id: str) -> str:
        """Generate a summary of the conversation window for context."""
        messages = self.get_conversation_window(session_id)

        if not messages:
            return "No conversation history available."

        context_lines = ["=== Conversation History ==="]
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("message", "")
            timestamp = msg.get("datetime", "")
            context_lines.append(f"[{role} @ {timestamp}]\n{content}\n")

        return "\n".join(context_lines)

    def clear_session(self, session_id: str) -> bool:
        """Clear all messages for a session."""
        if not self.redis_client:
            return False

        try:
            session_key = self._get_session_key(session_id)
            meta_key = self._get_session_meta_key(session_id)
            stats_key = self._get_stats_key(session_id)

            self.redis_client.delete(session_key)
            self.redis_client.delete(meta_key)
            self.redis_client.delete(stats_key)

            logger.info(f"Cleared session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
            return False

    def _update_session_metadata(self, session_id: str, role: str) -> None:
        """Update session metadata."""
        try:
            meta_key = self._get_session_meta_key(session_id)

            metadata = self.redis_client.hgetall(meta_key) or {
                "created_at": datetime.now().isoformat(),
                "user_messages": "0",
                "assistant_messages": "0",
            }

            metadata["last_activity"] = datetime.now().isoformat()

            if role == "user":
                metadata["user_messages"] = str(int(metadata.get("user_messages", 0)) + 1)
            elif role == "assistant":
                metadata["assistant_messages"] = str(int(metadata.get("assistant_messages", 0)) + 1)

            for key, value in metadata.items():
                self.redis_client.hset(meta_key, key, value)

            self.redis_client.expire(meta_key, WINDOW_TTL)
        except Exception as e:
            logger.debug(f"Error updating session metadata: {e}")

    def _update_statistics(self, session_id: str, role: str) -> None:
        """Update session statistics for monitoring."""
        try:
            stats_key = self._get_stats_key(session_id)

            self.redis_client.hincrby(stats_key, f"{role}_count", 1)
            self.redis_client.hincrby(stats_key, "total_messages", 1)
            self.redis_client.hset(stats_key, "last_modified", time.time())

            self.redis_client.expire(stats_key, WINDOW_TTL)
        except Exception as e:
            logger.debug(f"Error updating statistics: {e}")

    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session."""
        if not self.redis_client:
            return {}

        try:
            meta_key = self._get_session_meta_key(session_id)
            stats_key = self._get_stats_key(session_id)

            metadata = self.redis_client.hgetall(meta_key) or {}
            stats = self.redis_client.hgetall(stats_key) or {}

            return {
                "metadata": metadata,
                "statistics": stats,
                "window": self.get_conversation_window(session_id),
            }
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {}

    def get_all_sessions(self) -> List[str]:
        """Get list of all active sessions."""
        if not self.redis_client:
            return []

        try:
            pattern = "window_memory:session:*"
            keys = self.redis_client.keys(pattern)
            sessions = [key.replace("window_memory:session:", "") for key in keys]
            return sessions
        except Exception as e:
            logger.error(f"Error retrieving sessions: {e}")
            return []

    def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            if self.redis_client:
                self.redis_client.ping()
                return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
        return False


class SemanticSearchCache:
    """
    Redis-based semantic search caching for faster RAG.
    
    Features:
    - Cache embeddings for queries
    - Store search results with TTL
    - Query fingerprinting for deduplication
    - Cache hit tracking
    """

    def __init__(self, redis_url: str = REDIS_URL):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("✅ Redis connection established for Semantic Search Cache")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis for search cache: {e}")
            self.redis_client = None

    def _generate_query_key(self, query: str, category: Optional[str] = None, max_price: Optional[float] = None) -> str:
        """Generate a deterministic cache key for a search query."""
        query_signature = f"{query}|{category}|{max_price}"
        query_hash = hashlib.md5(query_signature.encode()).hexdigest()
        return f"semantic_search:query:{query_hash}"

    def _generate_embedding_key(self, query: str) -> str:
        """Generate cache key for embeddings."""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"semantic_search:embedding:{query_hash}"

    def cache_search_result(
        self,
        query: str,
        embedding: List[float],
        results: Dict[str, Any],
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        ttl: int = SEARCH_CACHE_TTL
    ) -> bool:
        """Cache a search result with its embedding."""
        if not self.redis_client:
            return False

        try:
            query_key = self._generate_query_key(query, category, max_price)
            embedding_key = self._generate_embedding_key(query)

            # Convert None values to JSON for Redis storage
            cached_data = {
                "query": query,
                "category": json.dumps(category),
                "max_price": json.dumps(max_price),
                "results": json.dumps(results),
                "cached_at": datetime.now().isoformat(),
                "hit_count": "0",
            }

            self.redis_client.hset(query_key, mapping=cached_data)
            self.redis_client.expire(query_key, ttl)

            # Handle None embeddings gracefully
            embedding_str = json.dumps(embedding) if embedding else json.dumps([])
            self.redis_client.setex(embedding_key, ttl, embedding_str)

            logger.debug(f"Cached search result for query: {query[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Error caching search result: {e}")
            return False

    def get_cached_result(self, query: str, category: Optional[str] = None, max_price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Retrieve cached sinfo result if available."""
        if not self.redis_client:
            return None

        try:
            query_key = self._generate_query_key(query, category, max_price)
            cached_data = self.redis_client.infoll(query_key)

            if not cached_data:
                logger.debug(f"Cache miss for query: {query[:50]}...")
                return None

            self.redis_client.hincrby(query_key, "hit_count", 1)

            results = json.loads(cached_data.get("results", "{}"))
            logger.debug(f"Cache hit for query: {query[:50]}... (hits: {cached_data.get('hit_count', 1)})")

            return {
                "results": results,
                "from_cache": True,
                "cached_at": cached_data.get("cached_at"),
                "hit_count": int(cached_data.get("hit_count", 0))
            }

        except Exception as e:
            logger.error(f"Error retrieving cached search result: {e}")
            return None

    def get_cached_embedding(self, query: str) -> Optional[List[float]]:
        """Retrieve cached embedding for a query."""
        if not self.redis_client:
            return None

        try:
            embedding_key = self._generate_embedding_key(query)
            embedding_str = self.redis_client.get(embedding_key)

            if embedding_str:
                return json.loads(embedding_str)

            return None

        except Exception as e:
            logger.error(f"Error retrieving cached embedding: {e}")
            return None

    def clear_search_cache(self) -> int:
        """Clear all search cache entries."""
        if not self.redis_client:
            return 0

        try:
            pattern = "semantic_search:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted_count} search cache entries")
                return deleted_count
            
            return 0

        except Exception as e:
            logger.error(f"Error clearing search cache: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the search cache."""
        if not self.redis_client:
            return {}

        try:
            query_keys = self.redis_client.keys("semantic_search:query:*")
            embedding_keys = self.redis_client.keys("semantic_search:embedding:*")

            total_hits = 0
            for key in query_keys:
                hit_count = self.redis_client.hget(key, "hit_count")
                if hit_count:
                    total_hits += int(hit_count)

            return {
                "cached_queries": len(query_keys),
                "cached_embeddings": len(embedding_keys),
                "total_hits": total_hits,
                "cache_size_info": self.redis_client.info("memory").get("used_memory_human", "N/A")
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    def health_check(self) -> bool:
        """Check Redis connection health for search cache."""
        try:
            if self.redis_client:
                self.redis_client.ping()
                return True
        except Exception as e:
            logger.error(f"Search cache health check failed: {e}")
        return False


class SlidingWindowTracker:
    """Track events/requests in a sliding time window (e.g., for rate limiting)."""

    def __init__(self, redis_client: redis.Redis, window_seconds: int = 60):
        """Initialize with Redis client and window size."""
        self.redis_client = redis_client
        self.window_seconds = window_seconds

    def record_event(self, identifier: str, amount: int = 1) -> int:
        """Record an event and return the count within the window."""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        key = f"window_tracker:{identifier}"

        try:
            self.redis_client.zremrangebyscore(key, 0, window_start)
            self.redis_client.zadd(key, {str(current_time): current_time})
            self.redis_client.expire(key, self.window_seconds + 1)

            count = self.redis_client.zcard(key)
            return count
        except Exception as e:
            logger.error(f"Error recording event: {e}")
            return 0

    def get_event_count(self, identifier: str) -> int:
        """Get event count within the sliding window."""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        key = f"window_tracker:{identifier}"

        try:
            self.redis_client.zremrangebyscore(key, 0, window_start)
            return self.redis_client.zcard(key)
        except Exception as e:
            logger.error(f"Error getting event count: {e}")
            return 0

    def is_within_limit(self, identifier: str, limit: int) -> bool:
        """Check if event count is within the specified limit."""
        return self.get_event_count(identifier) <= limit


# Global instances
_window_memory: Optional[WindowMemoryManager] = None
_search_cache: Optional[SemanticSearchCache] = None


def get_window_memory() -> WindowMemoryManager:
    """Get or create the global window memory instance."""
    global _window_memory
    if _window_memory is None:
        _window_memory = WindowMemoryManager()
    return _window_memory


def get_search_cache() -> SemanticSearchCache:
    """Get or create the global semantic search cache instance."""
    global _search_cache
    if _search_cache is None:
        _search_cache = SemanticSearchCache()
    return _search_cache
