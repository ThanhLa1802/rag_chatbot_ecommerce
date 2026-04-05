# Window Memory with Redis

## Overview

Window Memory is a Redis-based sliding window memory management system for storing and retrieving conversation history and request tracking. It automatically maintains a limited window of recent messages per session.

**Features:**
- ✅ Sliding window conversation history (configurable size)
- ✅ Automatic TTL expiration for old sessions
- ✅ Per-session memory isolation
- ✅ Message role support (user, assistant, system)
- ✅ Session statistics and metadata
- ✅ Event-based rate limiting with sliding windows
- ✅ Health checks and monitoring

---

## Architecture

```
Chat Request
    ↓
┌───────────────────────────────┐
│  Window Memory Manager        │
├───────────────────────────────┤
│ 1. Add User Message           │
│ 2. Retrieve Conversation      │
│ 3. Generate Context           │
│ 4. Store Assistant Response   │
└────────────────┬──────────────┘
                 ↓
            Redis Database
         (Session Storage)
```

### Redis Data Structure

```
window_memory:session:{session_id}
  - Sorted list of messages (JSON)
  - Size limited to WINDOW_SIZE
  - TTL: WINDOW_TTL seconds

window_memory:meta:{session_id}
  - Session metadata (created_at, last_activity, counts)
  - TTL: WINDOW_TTL seconds

window_memory:stats:{session_id}
  - Session statistics (message counts, timestamps)
  - TTL: WINDOW_TTL seconds

window_tracker:{identifier}
  - Sorted set for sliding window tracking
  - Used for rate limiting events
```

---

## Configuration

Set these environment variables to customize Window Memory:

```env
# Redis connection URL
REDIS_URL=redis://redis:6379/0

# Number of messages to keep in memory window
WINDOW_MEMORY_SIZE=5

# Time-to-live for sessions (seconds)
WINDOW_MEMORY_TTL=3600  # 1 hour
```

---

## API Usage

### 1. Chat with Session Memory

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me Laptops under 20 million VND"
  }' \
  -G --data-urlencode "session_id=user_123_session_1"
```

**Flow:**
1. User message stored in Redis
2. Conversation history retrieved as context
3. Enhanced prompt sent to LLM
4. Assistant response streamed and stored

---

### 2. Get Conversation History

```bash
curl http://localhost:8080/api/chat/history/user_123_session_1
```

**Response:**
```json
{
  "session_id": "user_123_session_1",
  "messages": [
    {
      "timestamp": 1712329334.123,
      "datetime": "2026-04-05T13:02:14.123456",
      "role": "user",
      "message": "Show me Laptops",
      "metadata": {}
    },
    {
      "timestamp": 1712329335.456,
      "datetime": "2026-04-05T13:02:15.456789",
      "role": "assistant",
      "message": "Here are the available laptops...",
      "metadata": {}
    }
  ],
  "statistics": {
    "user_count": "1",
    "assistant_count": "1",
    "total_messages": "2"
  },
  "message_count": 2
}
```

---

### 3. Clear Session History

```bash
curl -X DELETE http://localhost:8080/api/chat/history/user_123_session_1
```

**Response:**
```json
{
  "status": "success",
  "message": "Session user_123_session_1 cleared"
}
```

---

### 4. Check Window Memory Health

```bash
curl http://localhost:8080/api/chat/health
```

**Response:**
```json
{
  "status": "healthy",
  "redis_connected": true,
  "active_sessions": 15
}
```

---

## Code Integration Examples

### Basic Usage

```python
from app.services.window_memory import get_window_memory

# Get window memory instance
window_memory = get_window_memory()

# Add user message
window_memory.add_message(
    session_id="user_123",
    message="Hello, show me products",
    role="user",
    metadata={"ip": "192.168.1.1"}
)

# Retrieve conversation history
messages = window_memory.get_conversation_window("user_123")
print(f"Messages in window: {len(messages)}")

# Get formatted context
context = window_memory.get_context_summary("user_123")
print(context)

# Get session statistics
stats = window_memory.get_session_stats("user_123")
print(stats["metadata"])
print(stats["statistics"])
```

### Rate Limiting with Sliding Window

```python
from app.services.window_memory import SlidingWindowTracker
import redis

# Initialize tracker
redis_client = redis.from_url("redis://localhost:6379/0")
tracker = SlidingWindowTracker(redis_client, window_seconds=60)

# Record events
event_count = tracker.record_event("user_ip_192.168.1.1")
print(f"Events in last 60 seconds: {event_count}")

# Check if within limit
if tracker.is_within_limit("user_ip_192.168.1.1", limit=100):
    print("Rate limit OK")
else:
    print("Rate limit exceeded")
```

### Integration in Chat Service

```python
from fastapi import Query
from app.services.window_memory import get_window_memory

window_memory = get_window_memory()

@router.post("/chat")
async def chat_with_bot(
    request: ChatRequest,
    session_id: str = Query(..., description="Session ID for memory")
):
    # Store user message
    window_memory.add_message(
        session_id=session_id,
        message=request.query,
        role="user"
    )
    
    # Get conversation context
    context = window_memory.get_context_summary(session_id)
    
    # Use context in LLM prompt
    enhanced_prompt = f"{context}\n\nNew query: {request.query}"
    
    # Process with LLM...
    response = generate_response(enhanced_prompt)
    
    # Store assistant response
    window_memory.add_message(
        session_id=session_id,
        message=response,
        role="assistant"
    )
    
    return response
```

---

## Message Structure

```json
{
  "timestamp": 1712329334.123,
  "datetime": "2026-04-05T13:02:14.123456",
  "role": "user|assistant|system",
  "message": "Message content here",
  "metadata": {
    "key": "value",
    "source": "api|web|mobile"
  }
}
```

---

## Configuration Examples

### Small Window (Recent Messages Only)
```env
WINDOW_MEMORY_SIZE=3
WINDOW_MEMORY_TTL=600  # 10 minutes
```

### Large Window (Detailed History)
```env
WINDOW_MEMORY_SIZE=50
WINDOW_MEMORY_TTL=86400  # 24 hours
```

### Cloud Production
```env
REDIS_URL=redis://:password@redis-cloud.example.com:12345/0
WINDOW_MEMORY_SIZE=20
WINDOW_MEMORY_TTL=7200  # 2 hours
```

---

## Monitoring and Statistics

### View Active Sessions
```python
sessions = window_memory.get_all_sessions()
print(f"Active sessions: {len(sessions)}")
for session_id in sessions:
    stats = window_memory.get_session_stats(session_id)
    print(f"Session: {session_id}")
    print(f"  Created: {stats['metadata'].get('created_at')}")
    print(f"  Messages: {stats['statistics'].get('total_messages')}")
```

### Redis Commands for Monitoring

```bash
# Connect to Redis
redis-cli

# List all window memory keys
KEYS "window_memory:*"

# Get session details
LLEN "window_memory:session:user_123"
HGETALL "window_memory:meta:user_123"
HGETALL "window_memory:stats:user_123"

# Check memory usage
INFO memory
```

---

## Error Handling

```python
# Connection failure handling
window_memory = get_window_memory()
if not window_memory.health_check():
    logger.error("Window memory is unavailable")
    # Fallback to in-memory storage or cache
    use_fallback_memory()

# Message storage failure
success = window_memory.add_message(session_id, message, role)
if not success:
    logger.warning("Failed to store message in window memory")
    # Continue without persistent memory

# Session retrieval failure
messages = window_memory.get_conversation_window(session_id)
if not messages:
    logger.info(f"No history found for session {session_id}")
    messages = []
```

---

## Performance Characteristics

### Memory Usage
- Each message: ~500 bytes average
- Window of 5 messages: ~2.5 KB per session
- 1000 active sessions: ~2.5 MB

### Operation Latencies
- `add_message()`: ~5ms
- `get_conversation_window()`: ~3ms
- `get_context_summary()`: ~5ms
- Health check: ~1ms

---

## Cleanup and Maintenance

### Automatic Cleanup
- Sessions expire after WINDOW_TTL seconds
- Old messages are trimmed to WINDOW_SIZE
- Redis handles key expiration automatically

### Manual Cleanup
```python
# Clear specific session
window_memory.clear_session("user_123")

# Clear all sessions matching pattern
import redis
redis_client = redis.from_url(REDIS_URL)
keys = redis_client.keys("window_memory:*")
for key in keys:
    redis_client.delete(key)
```

### Monitoring Redis Memory
```bash
redis-cli INFO memory
# Monitor memory growth
redis-cli --stat
```

---

## Best Practices

1. **Use Descriptive Session IDs**
   ```python
   # Good
   session_id = f"user_{user_id}_{timestamp}_web"
   
   # Avoid
   session_id = "session_1"
   ```

2. **Handle Missing Context**
   ```python
   context = window_memory.get_context_summary(session_id)
   if not context or context == "No conversation history available.":
       context = "This is the start of a new conversation."
   ```

3. **Monitor Window Memory Health**
   ```python
   # Periodically check health
   if not window_memory.health_check():
       logger.critical("Window memory service is down!")
       # Alert and fallback
   ```

4. **Set Appropriate TTL**
   - Short sessions (support chat): 30 minutes
   - Regular conversations: 1-2 hours
   - Long-term tracking: 24 hours

5. **Backup Strategy**
   - Use Redis persistence (RDB/AOF)
   - Regular snapshots to database
   - Implement session export for important conversations

---

## Troubleshooting

### Problem: "Redis connection failed"
```python
# Check Redis is running
docker-compose logs redis

# Verify REDIS_URL
echo $REDIS_URL

# Test connection
redis-cli -u $REDIS_URL ping
```

### Problem: "Messages not persisting"
```python
# Check Redis is actually storing data
redis-cli KEYS "window_memory:*"

# Verify TTL not expiring too quickly
redis-cli TTL "window_memory:session:user_123"

# Check window size setting
echo $WINDOW_MEMORY_SIZE
```

### Problem: "Memory usage growing"
```python
# Monitor memory
redis-cli INFO memory

# Check for orphaned sessions
redis-cli KEYS "window_memory:session:*" | wc -l

# Manually clear old sessions
redis-cli EVAL "
  for i, key in ipairs(redis.call('KEYS', 'window_memory:*')) do
    redis.call('DEL', key)
  end
"
```

---

## Future Enhancements

- [ ] Compression for large messages
- [ ] Distributed window memory across Redis cluster
- [ ] Message search and filtering
- [ ] Analytics dashboard
- [ ] Persistence to long-term storage
- [ ] Multi-tenant support
- [ ] End-to-end encryption for sensitive conversations
- [ ] Integration with message queue (RabbitMQ/Kafka)
