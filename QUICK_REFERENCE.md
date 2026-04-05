# Window Memory - Developer Quick Reference

## Quick Links

- **Full Documentation**: [WINDOW_MEMORY.md](WINDOW_MEMORY.md)
- **Implementation Details**: [WINDOW_MEMORY_IMPLEMENTATION.md](WINDOW_MEMORY_IMPLEMENTATION.md)
- **Deployment Guide**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **API Documentation**: `http://localhost:8080/docs` (running server)

## 30-Second Overview

Window Memory tracks conversation context by:
1. Storing each message in Redis with a session ID
2. Keeping only the last N messages (sliding window)
3. Auto-expanding LLM context with conversation history
4. Automatic cleanup after TTL expiration

## Common Tasks

### Task: Start Using Window Memory

```python
from app.services.window_memory import get_window_memory

# Get singleton instance
memory = get_window_memory()

# Store a message
memory.add_message(
    session_id="user-123",
    message="Show me laptops under 30 million",
    role="user"
)

# Get conversation history
history = memory.get_conversation_window("user-123")
context = memory.get_context_summary("user-123")

# Clear session
memory.clear_session("user-123")
```

### Task: Send a Chat Message with Context

```bash
SESSION_ID=$(uuidgen)

# Message 1
curl -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"query": "What phones do you have?"}'

# Message 2 (has context from message 1)
curl -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"query": "Which is the cheapest?"}'

# View full conversation
curl "http://localhost:8080/api/chat/history/$SESSION_ID" | jq .
```

### Task: Monitor System Health

```bash
# Check Redis connection
curl http://localhost:8080/api/chat/health

# Monitor Redis directly
redis-cli KEYS "window_memory:*" | wc -l    # Active sessions
redis-cli INFO memory | grep used_memory    # Memory usage

# View specific session
SESSION_ID="your-session-id"
redis-cli LRANGE "window_memory:session:$SESSION_ID" 0 -1
```

### Task: Debug a Session

```bash
SESSION_ID="problematic-session"

# Check if session exists
redis-cli EXISTS "window_memory:session:$SESSION_ID"

# View all messages
redis-cli LRANGE "window_memory:session:$SESSION_ID" 0 -1

# Check metadata
redis-cli HGETALL "window_memory:meta:$SESSION_ID"

# Check statistics
redis-cli HGETALL "window_memory:stats:$SESSION_ID"

# Check TTL
redis-cli TTL "window_memory:session:$SESSION_ID"

# Force clear if needed
redis-cli DEL "window_memory:session:$SESSION_ID"
redis-cli DEL "window_memory:meta:$SESSION_ID"
redis-cli DEL "window_memory:stats:$SESSION_ID"
```

### Task: Test with Python Client

```bash
# Interactive chat
python app/services/window_memory_client.py interactive

# Batch test
python app/services/window_memory_client.py batch

# Monitor sessions
python app/services/window_memory_client.py monitor
```

### Task: Configure for Different Scenarios

```bash
# Development (large window, long TTL, verbose logs)
export WINDOW_MEMORY_SIZE=20
export WINDOW_MEMORY_TTL=7200
export LOG_LEVEL=DEBUG

# Production (small window, medium TTL)
export WINDOW_MEMORY_SIZE=5
export WINDOW_MEMORY_TTL=1800
export LOG_LEVEL=INFO

# High Traffic (minimal window, short TTL, Redis persistence)
export WINDOW_MEMORY_SIZE=3
export WINDOW_MEMORY_TTL=900
redis-cli BGSAVE  # Enable persistence
```

## API Endpoints

### POST /api/chat - Send Message

```bash
curl -X POST "http://localhost:8080/api/chat?session_id=SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"query": "Your question here"}'
```

**Response**: Streamed text response with context awareness

### GET /api/chat/history/{session_id} - Get Conversation

```bash
curl "http://localhost:8080/api/chat/history/SESSION_ID"
```

**Response**:
```json
{
  "session_id": "SESSION_ID",
  "messages": [{...}, {...}],
  "statistics": {"user_count": "2", "assistant_count": "2"},
  "message_count": 4
}
```

### DELETE /api/chat/history/{session_id} - Clear Session

```bash
curl -X DELETE "http://localhost:8080/api/chat/history/SESSION_ID"
```

**Response**: `{"status": "success", "message": "Session SESSION_ID cleared"}`

### GET /api/chat/health - Check Health

```bash
curl "http://localhost:8080/api/chat/health"
```

**Response**:
```json
{
  "status": "healthy",
  "redis_connected": true,
  "active_sessions": 42
}
```

## Code Examples

### Example 1: Integration into FastAPI Route

```python
from fastapi import FastAPI, Query
from app.services.window_memory import get_window_memory
from app.services.rag_service import generate_answer_stream

app = FastAPI()
memory = get_window_memory()

@app.post("/my-chat")
async def my_chat_endpoint(query: str, session_id: str = Query(...)):
    # Store user message
    memory.add_message(session_id, query, "user")
    
    # Get context
    context = memory.get_context_summary(session_id)
    
    # Generate response with context
    answer = generate_answer_stream(context + "\n" + query)
    
    # Store response
    full_response = ""
    for chunk in answer:
        full_response += chunk
    
    memory.add_message(session_id, full_response, "assistant")
    
    return {"response": full_response}
```

### Example 2: Testing Rate Limiting

```python
from app.services.window_memory import SlidingWindowTracker
import redis

client = redis.from_url("redis://localhost:6379/0")
tracker = SlidingWindowTracker(client, window_seconds=60)

# Track API calls per user
user_id = "user-123"

if tracker.is_within_limit(user_id, 100):  # Max 100 requests/minute
    tracker.record_event(user_id)
    # Process request
else:
    # Rate limited
    return {"error": "Too many requests"}
```

### Example 3: Batch Processing Sessions

```python
from app.services.window_memory import get_window_memory

memory = get_window_memory()

# Get all active sessions
sessions = memory.get_all_sessions()
print(f"Active sessions: {len(sessions)}")

# Process each session
for session_id in sessions:
    stats = memory.get_session_stats(session_id)
    print(f"{session_id}: {stats['statistics']['total_messages']} messages")
    
    # Example: Archive old sessions
    created_at = stats['metadata']['created_at']
    if is_older_than(created_at, hours=24):
        memory.clear_session(session_id)
```

## Troubleshooting Checklist

- [ ] Redis running? `redis-cli ping` → should return `PONG`
- [ ] Redis accessible? `telnet localhost 6379`
- [ ] Python redis package installed? `pip list | grep redis`
- [ ] Environment variables set? `echo $REDIS_URL`
- [ ] Same session_id used? `curl ... ?session_id=SAME_ID`
- [ ] TTL not expired? `redis-cli TTL window_memory:session:ID`
- [ ] Window size not exceeded? `redis-cli LLEN window_memory:session:ID`

## Performance Tips

1. **Reduce window size for speed**: Smaller window = faster retrieval
2. **Use shorter TTL in production**: Prevents memory bloat
3. **Monitor Redis memory**: Alert at 80% usage
4. **Batch clear sessions**: Run cleanup scripts during off-peak hours
5. **Consider Redis Cluster**: For 1000+ concurrent sessions

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `Redis connection failed` | Check `REDIS_URL`, restart Redis |
| `No messages in history` | Verify same `session_id` used |
| `Session not found` | Session expired (TTL) or cleared |
| `Memory bloat` | Reduce `WINDOW_MEMORY_SIZE` or `WINDOW_MEMORY_TTL` |
| `Slow responses` | Check Redis latency, reduce window size |

## Next Steps

1. **Run tests**: `python app/services/window_memory_client.py interactive`
2. **Check health**: `curl http://localhost:8080/api/chat/health`
3. **Monitor**: Watch Redis memory and connection
4. **Optimize**: Adjust settings based on your usage patterns
5. **Deploy**: When ready for production

## File Locations

| File | Purpose | Size |
|------|---------|------|
| [app/services/window_memory.py](app/services/window_memory.py) | Core implementation | 380 lines |
| [app/api/chat_routers.py](app/api/chat_routers.py) | API endpoints | 135 lines |
| [app/services/window_memory_client.py](app/services/window_memory_client.py) | Testing client | 250 lines |
| [WINDOW_MEMORY.md](WINDOW_MEMORY.md) | Full documentation | 200+ lines |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Setup & deployment | 350+ lines |

## Key Concepts

- **Session**: Unique conversation context identified by `session_id`
- **Window**: Last N messages kept (configurable, default: 5)
- **TTL**: Time-to-live before automatic cleanup (default: 3600s = 1 hour)
- **Context**: Formatted conversation history fed to LLM
- **Role**: Message type - "user", "assistant", or "system"
- **Metadata**: Additional info attached to messages

## Redis Data Structure Reference

```
window_memory:session:SESSION_ID      → List of messages (JSON strings)
window_memory:meta:SESSION_ID         → Hash with created_at, last_activity
window_memory:stats:SESSION_ID        → Hash with user_count, assistant_count
window_memory:events:IDENTIFIER       → Sorted set for event tracking
```

---

**Version**: 1.0  
**Last Updated**: 2024-01-15  
**Status**: Production Ready ✅
