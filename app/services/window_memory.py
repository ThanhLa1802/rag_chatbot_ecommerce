"""
Window Memory Service using Redis
Implements a sliding window conversation memory for chat history and context management.
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import redis

logger = logging.getLogger(__name__)

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
WINDOW_SIZE = int(os.getenv("WINDOW_MEMORY_SIZE", "5"))  # Number of messages to keep
WINDOW_TTL = int(os.getenv("WINDOW_MEMORY_TTL", "1800"))  # Time-to-live in seconds (1 hour)


class WindowMemoryManager:
    """
    Manages conversation history using Redis with sliding window mechanism.
    
    Features:
    - Store conversation messages in time-ordered windows
    - Automatic cleanup of old messages (TTL)
    - Per-session memory isolation
    - Message type support (user, assistant, system)
    - Analytics and statistics
    """

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
        """Generate Redis key for session."""
        return f"window_memory:session:{session_id}"

    def _get_session_meta_key(self, session_id: str) -> str:
        """Generate Redis key for session metadata."""
        return f"window_memory:meta:{session_id}"

    def _get_stats_key(self, session_id: str) -> str:
        """Generate Redis key for session statistics."""
        return f"window_memory:stats:{session_id}"

    def add_message(
        self,
        session_id: str,
        message: str,
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a message to the session's conversation window.
        
        Args:
            session_id: Unique session identifier
            message: Message content
            role: Message role ('user', 'assistant', 'system')
            metadata: Optional metadata dict
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.redis_client:
            logger.warning("Redis client not available, skipping message storage")
            return False

        try:
            session_key = self._get_session_key(session_id)
            timestamp = time.time()

            # Create message object
            msg_obj = {
                "timestamp": timestamp,
                "datetime": datetime.now().isoformat(),
                "role": role,
                "message": message,
                "metadata": json.dumps(metadata or {}),
            }

            # Push to Redis list (right push for FIFO)
            self.redis_client.rpush(session_key, json.dumps(msg_obj))

            # Trim to window size (keep only last WINDOW_SIZE messages)
            self.redis_client.ltrim(session_key, -WINDOW_SIZE, -1)

            # Set TTL on session key
            self.redis_client.expire(session_key, WINDOW_TTL)

            # Update session metadata
            self._update_session_metadata(session_id, role)

            # Update statistics
            self._update_statistics(session_id, role)

            logger.debug(f"Added {role} message to session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding message to window memory: {e}")
            return False

    def get_conversation_window(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve conversation history for a session within the window.
        
        Args:
            session_id: Session identifier
            limit: Optional limit on number of messages to retrieve
            
        Returns:
            List of message dictionaries in chronological order
        """
        if not self.redis_client:
            logger.warning("Redis client not available, returning empty history")
            return []

        try:
            session_key = self._get_session_key(session_id)
            limit = limit or WINDOW_SIZE

            # Get all messages from the window
            messages_data = self.redis_client.lrange(session_key, -limit, -1)

            # Parse and return messages
            messages = []
            for msg_data in messages_data:
                try:
                    msg = json.loads(msg_data)
                    msg["metadata"] = json.loads(msg["metadata"])
                    messages.append(msg)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse message: {msg_data}")
                    continue

            logger.debug(f"Retrieved {len(messages)} messages from session {session_id}")
            return messages

        except Exception as e:
            logger.error(f"Error retrieving conversation window: {e}")
            return []

    def get_latest_message(self, session_id: str) -> Optional[Dict]:
        """Get the most recent message in the session."""
        messages = self.get_conversation_window(session_id, limit=1)
        return messages[-1] if messages else None

    def get_context_summary(self, session_id: str) -> str:
        """
        Generate a summary of the conversation window for context.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Formatted string of conversation context
        """
        messages = self.get_conversation_window(session_id)

        if not messages:
            return "No conversation history available."

        # Build context string
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
        """Update session metadata (creation time, last activity, etc.)."""
        try:
            meta_key = self._get_session_meta_key(session_id)

            metadata = self.redis_client.hgetall(meta_key) or {
                "created_at": datetime.now().isoformat(),
                "user_messages": "0",
                "assistant_messages": "0",
            }

            metadata["last_activity"] = datetime.now().isoformat()

            # Count messages by role
            if role == "user":
                metadata["user_messages"] = str(int(metadata.get("user_messages", 0)) + 1)
            elif role == "assistant":
                metadata["assistant_messages"] = str(
                    int(metadata.get("assistant_messages", 0)) + 1
                )

            for key, value in metadata.items():
                self.redis_client.hset(meta_key, key, value)

            self.redis_client.expire(meta_key, WINDOW_TTL)
        except Exception as e:
            logger.debug(f"Error updating session metadata: {e}")

    def _update_statistics(self, session_id: str, role: str) -> None:
        """Update session statistics for monitoring."""
        try:
            stats_key = self._get_stats_key(session_id)

            # Increment role counter
            self.redis_client.hincrby(stats_key, f"{role}_count", 1)

            # Update total messages
            self.redis_client.hincrby(stats_key, "total_messages", 1)

            # Update last modified timestamp
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
            # Extract session IDs from keys
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


class SlidingWindowTracker:
    """
    Track events/requests in a sliding time window (e.g., for rate limiting).
    """

    def __init__(self, redis_client: redis.Redis, window_seconds: int = 60):
        """
        Args:
            redis_client: Redis client instance
            window_seconds: Size of the sliding window in seconds
        """
        self.redis_client = redis_client
        self.window_seconds = window_seconds

    def record_event(self, identifier: str, amount: int = 1) -> int:
        """
        Record an event and return the count within the window.
        
        Args:
            identifier: Unique identifier (e.g., user_id, ip_address)
            amount: Number of events to record
            
        Returns:
            Current count within the window
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds
        key = f"window_tracker:{identifier}"

        try:
            # Remove old entries outside the window
            self.redis_client.zremrangebyscore(key, 0, window_start)

            # Add new event with current timestamp
            self.redis_client.zadd(key, {str(current_time): current_time})

            # Set expiration
            self.redis_client.expire(key, self.window_seconds + 1)

            # Get count within window
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
            # Remove old entries
            self.redis_client.zremrangebyscore(key, 0, window_start)

            # Return count
            return self.redis_client.zcard(key)
        except Exception as e:
            logger.error(f"Error getting event count: {e}")
            return 0

    def is_within_limit(self, identifier: str, limit: int) -> bool:
        """Check if event count is within the specified limit."""
        return self.get_event_count(identifier) <= limit


# Global instance
_window_memory: Optional[WindowMemoryManager] = None


def get_window_memory() -> WindowMemoryManager:
    """Get or create the global window memory instance."""
    global _window_memory
    if _window_memory is None:
        _window_memory = WindowMemoryManager()
    return _window_memory
