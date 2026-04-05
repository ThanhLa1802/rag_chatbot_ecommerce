# Window Memory System - Deployment & Testing Guide

## Overview

This guide covers deployment, testing, monitoring, and troubleshooting of the Window Memory system for the e-commerce RAG pipeline.

## Quick Start

### 1. Prepare Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set your values:
# - DATABASE_URL: MySQL connection string
# - QDRANT_URL: Qdrant server URL
# - OPENAI_API_KEY: Your OpenAI API key
# - REDIS_URL: Redis connection string
# - DEBUG: true/false
# - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR
```

### 2. Build and Start Services

```bash
# Build images and start all services
docker-compose up --build

# Or start in background
docker-compose up --build -d

# View logs
docker-compose logs -f rag_api
docker-compose logs -f celery_worker
docker-compose logs -f redis
```

### 3. Verify Services Are Running

```bash
# Check service status
docker-compose ps

# Access API documentation
# http://localhost:8080/docs

# Test health endpoints
curl http://localhost:8080/
curl http://localhost:8080/api/chat/health
```

## Testing Window Memory

### Test 1: Basic Connectivity

```bash
# Check Redis connection
REDIS_HOST=localhost
redis-cli -h $REDIS_HOST ping

# Check API health
curl -X GET "http://localhost:8080/api/chat/health"
```

Expected response:
```json
{
  "status": "healthy",
  "redis_connected": true,
  "active_sessions": 0
}
```

### Test 2: Single Message

```bash
# Send a single message to a new session
SESSION_ID=$(uuidgen)

curl -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me all phones under 20 million", "category": null, "max_price": null}'
```

Expected: Streamed response from the AI assistant

### Test 3: Multi-Message Conversation

```bash
#!/bin/bash

SESSION_ID=$(uuidgen)
echo "Session ID: $SESSION_ID"

# Message 1
echo -e "\n=== Message 1 ==="
curl -s -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"query": "What phones do you have?"}'

# Message 2
echo -e "\n=== Message 2 ==="
curl -s -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the price of the cheapest one?"}'

# Message 3
echo -e "\n=== Message 3 ==="
curl -s -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"query": "Do you have any discounts?"}'

# View history
echo -e "\n=== Conversation History ==="
curl -s -X GET "http://localhost:8080/api/chat/history/$SESSION_ID" | jq .
```

### Test 4: Using the Python Client

```bash
# Run interactive chat
python app/services/window_memory_client.py interactive

# Run batch conversations
python app/services/window_memory_client.py batch

# Monitor sessions
python app/services/window_memory_client.py monitor
```

### Test 5: Conversation History Retrieval

```bash
SESSION_ID="your-session-id"

# Get full history with statistics
curl -X GET "http://localhost:8080/api/chat/history/$SESSION_ID" | jq .

# Expected response with:
# - messages: array of all messages in window
# - statistics: user_count, assistant_count, etc.
# - message_count: total messages in current window
```

Response format:
```json
{
  "session_id": "uuid",
  "messages": [
    {
      "timestamp": 1234567890.5,
      "datetime": "2024-01-15T10:30:45.123456",
      "role": "user",
      "message": "Show me laptops under 30 million",
      "metadata": {}
    },
    {
      "timestamp": 1234567891.2,
      "datetime": "2024-01-15T10:30:46.234567",
      "role": "assistant",
      "message": "Here are the available laptops...",
      "metadata": {"response_completed_at": "2024-01-15T10:30:50"}
    }
  ],
  "statistics": {
    "user_count": "1",
    "assistant_count": "1",
    "total_messages": "2",
    "last_modified": "1234567891.5"
  },
  "message_count": 2
}
```

### Test 6: Session Clearing

```bash
SESSION_ID="your-session-id"

# Clear session history
curl -X DELETE "http://localhost:8080/api/chat/history/$SESSION_ID"

# Verify it's cleared
curl -X GET "http://localhost:8080/api/chat/history/$SESSION_ID"
```

## Monitoring & Debugging

### Redis Commands for Monitoring

```bash
# Connect to Redis
redis-cli

# View all window memory keys
KEYS "window_memory:*"

# View session messages
LLEN "window_memory:session:SESSION_ID"
LRANGE "window_memory:session:SESSION_ID" 0 -1

# View session metadata
HGETALL "window_memory:meta:SESSION_ID"

# View session statistics
HGETALL "window_memory:stats:SESSION_ID"

# Check TTL
TTL "window_memory:session:SESSION_ID"

# Monitor events in real-time
MONITOR

# Check memory usage
INFO memory
```

### Log Analysis

```bash
# View API logs
docker-compose logs rag_api | grep "window_memory\|Window Memory"

# View worker logs
docker-compose logs celery_worker

# Follow Redis logs (if using default logging)
tail -f /var/lib/redis/dump.rdb

# Check for errors
docker-compose logs | grep ERROR
```

### Performance Metrics

```bash
# Check active sessions count
curl http://localhost:8080/api/chat/health | jq .active_sessions

# Monitor Redis memory
redis-cli INFO memory

# Check message latency (from logs)
docker-compose logs rag_api | grep "Assistant response stored"
```

## Common Issues & Solutions

### Issue 1: Redis Connection Failed

```
Error: Redis connection failed: Connection refused
```

**Solution:**
```bash
# Check if Redis is running
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis

# Verify connection
redis-cli ping
```

### Issue 2: Session Data Not Persisting

```
Problem: Messages stored but not retrieved in next request
```

**Possible Causes & Solutions:**
1. **TTL Expired**: Check WINDOW_MEMORY_TTL in .env (default: 3600 seconds)
2. **Wrong Session ID**: Ensure same session_id is used
3. **Window Size Exceeded**: Messages older than WINDOW_MEMORY_SIZE (default: 5) are removed
4. **Memory Full**: Redis memory limit reached

**Debug:**
```bash
# Check session exists
redis-cli EXISTS "window_memory:session:SESSION_ID"

# Check TTL
redis-cli TTL "window_memory:session:SESSION_ID"

# Check message count
redis-cli LLEN "window_memory:session:SESSION_ID"

# View memory usage
redis-cli INFO memory
```

### Issue 3: Message Storage Failed

```
Error: Error adding message to window memory
```

**Solution:**
```bash
# Check Redis connection
redis-cli ping

# Check Redis logs
docker-compose logs redis

# Verify Redis URL in .env
echo $REDIS_URL

# Restart API service
docker-compose restart rag_api
```

### Issue 4: Streaming Response Stuck

```
Problem: Chat endpoint responds slowly or times out
```

**Debug Steps:**
1. Check API logs for errors:
```bash
docker-compose logs -f rag_api | grep "chat"
```

2. Check Qdrant is responding:
```bash
curl http://localhost:6333/health
```

3. Check OpenAI API connectivity:
```bash
# Test with small query
curl -X POST "http://localhost:8080/api/chat?session_id=test" \
  -H "Content-Type: application/json" \
  -d '{"query": "hello"}'
```

### Issue 5: High Memory Usage

**Causes:**
- Too many active sessions
- WINDOW_MEMORY_TTL too high
- Message size too large

**Solutions:**
```bash
# Reduce TTL
export WINDOW_MEMORY_TTL=1800  # 30 minutes instead of 1 hour

# Reduce window size
export WINDOW_MEMORY_SIZE=3    # Keep last 3 messages only

# Clear old sessions manually
redis-cli DEL $(redis-cli KEYS "window_memory:*" | head -100)

# Monitor memory
watch -n 1 'redis-cli INFO memory | grep used_memory_human'
```

## Configuration Tuning

### Environment Variables

```bash
# Window Memory Configuration
WINDOW_MEMORY_SIZE=5          # Number of messages to keep (default: 5)
WINDOW_MEMORY_TTL=3600        # Session TTL in seconds (default: 1 hour)
REDIS_URL=redis://redis:6379/0

# API Configuration  
DEBUG=false
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-your-key
QDRANT_URL=http://qdrant_db:6333
DATABASE_URL=mysql+pymysql://root:password@mysql_db:3306/ecommerce
```

### Optimal Settings by Use Case

**Development:**
```bash
WINDOW_MEMORY_SIZE=10
WINDOW_MEMORY_TTL=7200
LOG_LEVEL=DEBUG
DEBUG=true
```

**Production:**
```bash
WINDOW_MEMORY_SIZE=5
WINDOW_MEMORY_TTL=1800
LOG_LEVEL=INFO
DEBUG=false
```

**High Traffic:**
```bash
WINDOW_MEMORY_SIZE=3
WINDOW_MEMORY_TTL=900
# Use Redis persistence and clustering
```

## Load Testing

### Basic Load Test

```bash
#!/bin/bash

# Test with multiple concurrent sessions
SESSION_IDS=()
for i in {1..5}; do
  SESSION_IDS+=($(uuidgen))
done

# Send messages concurrently
for SESSION_ID in "${SESSION_IDS[@]}"; do
  (
    for j in {1..3}; do
      curl -s -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
        -H "Content-Type: application/json" \
        -d '{"query": "Show me products under 10 million"}' > /dev/null
    done
    echo "Session $SESSION_ID completed"
  ) &
done

wait
echo "Load test completed"
```

### Using Apache Bench

```bash
# Single request
ab -c 1 -n 1 http://localhost:8080/

# Concurrent requests
ab -c 10 -n 100 -p data.json -T application/json http://localhost:8080/api/products
```

### Using Locust for Advanced Testing

```python
from locust import HttpUser, task, between

class ChatUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        self.session_id = str(uuid.uuid4())
    
    @task
    def send_message(self):
        self.client.post(
            f"/api/chat?session_id={self.session_id}",
            json={"query": "Show me phones under 20 million"}
        )

# Run: locust -f locustfile.py --host=http://localhost:8080
```

## Backup & Recovery

### Backup Redis Data

```bash
# One-time backup
docker-compose exec redis redis-cli BGSAVE

# Copy backup file
docker-compose exec redis cat /data/dump.rdb > redis_backup.rdb

# Automatic backups (add to docker-compose.yml)
volumes:
  - redis_data:/data
  - ./backups:/backups
```

### Recovery from Backup

```bash
# Copy backup back
docker cp redis_backup.rdb container_name:/data/dump.rdb

# Restart Redis
docker-compose restart redis
```

## Maintenance Tasks

### Daily

- Monitor Redis memory usage: `redis-cli INFO memory`
- Check for error logs: `docker-compose logs | grep ERROR`
- Verify health: `curl http://localhost:8080/api/chat/health`

### Weekly

- Clean up old sessions (> 7 days old)
- Check database size: `docker-compose exec mysql_db du -h`
- Review performance metrics

### Monthly

- Full backup of all services
- Performance tuning review
- Dependency updates check

## Production Deployment Checklist

- [ ] .env configured with production values
- [ ] Redis persistence enabled
- [ ] Redis backups configured
- [ ] Monitoring setup (Prometheus, New Relic, etc.)
- [ ] Logging aggregation (ELK, Datadog, etc.)
- [ ] Rate limiting configured
- [ ] SSL/TLS enabled
- [ ] Database backups automated
- [ ] Load testing completed
- [ ] Rollback plan documented
- [ ] Incident response plan ready
- [ ] API rate limiting deployed
- [ ] Authentication enabled (if needed)

## Next Steps

1. **Testing**: Run through all test cases above
2. **Optimization**: Tune WINDOW_MEMORY_SIZE and TTL based on usage patterns
3. **Monitoring**: Set up alerts and dashboards
4. **Documentation**: Document your specific deployment configuration
5. **Training**: Ensure team knows how to maintain and troubleshoot

## Support & Resources

- **Redis Documentation**: https://redis.io/docs/
- **OpenAI API**: https://platform.openai.com/docs/
- **Qdrant Documentation**: https://qdrant.tech/documentation/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Docker Compose**: https://docs.docker.com/compose/
