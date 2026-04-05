# Window Memory - First Time Deployment Checklist

## Pre-Deployment (Setup & Configuration)

### Environment Setup
- [ ] `.env` file created from `.env.example`
- [ ] `DATABASE_URL` set: `mysql+pymysql://root:password@localhost:3307/ecommerce`
- [ ] `REDIS_URL` set: `redis://localhost:6379/0`
- [ ] `QDRANT_URL` set: `http://localhost:6333`
- [ ] `OPENAI_API_KEY` set with valid key
- [ ] `WINDOW_MEMORY_SIZE` set to 5 (or custom value)
- [ ] `WINDOW_MEMORY_TTL` set to 3600 (or custom value)
- [ ] `LOG_LEVEL` set to DEBUG (change to INFO for production)
- [ ] `DEBUG` flag set appropriately

### Code Review
- [ ] `app/services/window_memory.py` contains 380+ lines
- [ ] `app/api/chat_routers.py` has window memory integration
- [ ] `app/services/window_memory_client.py` exists for testing
- [ ] All imports are present (redis, json, logging, datetime)
- [ ] No syntax errors in files

### Docker Setup
- [ ] `docker-compose.yml` includes Redis service
- [ ] `docker-compose.yml` includes MySQL, Qdrant, Celery services
- [ ] Volume mappings are correct
- [ ] Port mappings are not conflicting:
  - [ ] Port 8080 available for API
  - [ ] Port 6379 available for Redis
  - [ ] Port 3307 available for MySQL
  - [ ] Port 6333 available for Qdrant

## Deployment (Build & Start)

### Build Phase
- [ ] Run: `docker-compose up --build`
- [ ] Wait for all services to start
- [ ] Check no Docker build errors
- [ ] Verify service containers started: `docker-compose ps`

### Service Health
- [ ] Redis service shows "Up" status
- [ ] MySQL service shows "Up" status
- [ ] Qdrant service shows "Up" status
- [ ] API service (rag_api) shows "Up" status
- [ ] Celery worker service shows "Up" status

### Initial Connectivity Tests
- [ ] Redis connectivity: `redis-cli ping` → PONG
- [ ] MySQL connectivity: `docker-compose exec mysql_db mysql -uroot -ppassword`
- [ ] Qdrant connectivity: `curl http://localhost:6333/health`
- [ ] API health: `curl http://localhost:8080/` → 200 OK
- [ ] Chat health: `curl http://localhost:8080/api/chat/health` → status: "healthy"

## Testing (Validation Phase)

### Test 1: Basic API Connectivity
```bash
# Expected: 200 OK
curl http://localhost:8080/

# Expected: {"status": "healthy", ...}
curl http://localhost:8080/api/chat/health
```
- [ ] Root endpoint responds
- [ ] Health endpoint shows healthy
- [ ] Redis connected = true

### Test 2: Single Message Session
```bash
SESSION_ID=$(uuidgen)
curl -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello"}'
```
- [ ] Request succeeds (no 500 errors)
- [ ] Response received (not empty)
- [ ] No Redis connection errors in logs
- [ ] No timeout errors

### Test 3: Message Storage Verification
```bash
redis-cli LLEN "window_memory:session:$SESSION_ID"
redis-cli LRANGE "window_memory:session:$SESSION_ID" 0 -1
```
- [ ] Message exists in Redis
- [ ] Message count == 2 (user + assistant)
- [ ] Messages contain correct content

### Test 4: History Retrieval
```bash
curl "http://localhost:8080/api/chat/history/$SESSION_ID" | jq .
```
- [ ] History endpoint responds (200 OK)
- [ ] Contains "messages" array
- [ ] Contains "statistics" object
- [ ] message_count matches Redis LLEN

### Test 5: Multi-Message Conversation
```bash
# Send 3+ messages to same session
for i in {1..3}; do
  curl -s -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
    -d '{"query": "Message '$i'"}' > /dev/null
done

# Verify all stored
curl "http://localhost:8080/api/chat/history/$SESSION_ID" | jq '.message_count'
```
- [ ] All messages stored
- [ ] Message count increases correctly
- [ ] No message loss

### Test 6: Session Isolation
```bash
SESSION_A=$(uuidgen)
SESSION_B=$(uuidgen)

# Separate conversations
curl -s -X POST "http://localhost:8080/api/chat?session_id=$SESSION_A" \
  -d '{"query": "Session A message"}'
curl -s -X POST "http://localhost:8080/api/chat?session_id=$SESSION_B" \
  -d '{"query": "Session B message"}'

# Verify isolation
redis-cli LRANGE "window_memory:session:$SESSION_A" 0 -1  # Should show A's messages
redis-cli LRANGE "window_memory:session:$SESSION_B" 0 -1  # Should show B's messages
```
- [ ] Session A has different messages than B
- [ ] No message cross-contamination
- [ ] Each session maintains own history

### Test 7: Session Clearing
```bash
curl -X DELETE "http://localhost:8080/api/chat/history/$SESSION_ID"
curl "http://localhost:8080/api/chat/history/$SESSION_ID" | jq '.message_count'
```
- [ ] DELETE request succeeds
- [ ] Afterwards message_count = 0
- [ ] Redis key deleted
- [ ] No error on re-deletion

### Test 8: TTL Expiration
```bash
# Check TTL
redis-cli TTL "window_memory:session:$SESSION_ID"  # Should be positive number

# Wait and recheck (requires full WINDOW_MEMORY_TTL wait)
sleep 3600
redis-cli EXISTS "window_memory:session:$SESSION_ID"  # Should be 0
```
- [ ] TTL shows seconds remaining
- [ ] Session auto-deletes after TTL
- [ ] No manual cleanup needed

### Test 9: Context Awareness (Manual Review)
```bash
SESSION_ID=$(uuidgen)

# Message 1
curl -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
  -d '{"query": "What products are available?"}'

# Message 2
curl -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
  -d '{"query": "Tell me more about the price"}'
```
- [ ] Response to message 2 references message 1 context
- [ ] LLM shows understanding of conversation flow
- [ ] Not treating as isolated queries

### Test 10: Python Client Testing
```bash
python app/services/window_memory_client.py interactive
```
- [ ] Client connects successfully
- [ ] Health check shows "Healthy"
- [ ] Can send and receive messages
- [ ] History displays correctly
- [ ] Statistics show correct counts

### Test 11: Concurrent Sessions
```bash
# Run multiple session tests in parallel
for i in {1..5}; do
  SESSION_ID=$(uuidgen)
  # Send message to each session
  curl -s -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
    -d '{"query": "Test message '$i'"}' &
done
wait

# Check health
curl http://localhost:8080/api/chat/health | jq '.active_sessions'
```
- [ ] All requests succeeded
- [ ] Active sessions count increased
- [ ] No race conditions
- [ ] No connection pool exhaustion

### Test 12: Error Handling
```bash
# Empty query
curl -X POST "http://localhost:8080/api/chat?session_id=test" \
  -d '{"query": ""}'

# Missing session_id
curl -X POST "http://localhost:8080/api/chat" \
  -d '{"query": "test"}'

# Invalid JSON
curl -X POST "http://localhost:8080/api/chat?session_id=test" \
  -d 'invalid'
```
- [ ] Empty query handled gracefully
- [ ] Missing session_id returns 422 error
- [ ] Invalid JSON returns 422 error
- [ ] No server crashes

### Test 13: Monitoring Commands
```bash
# Check all keys
redis-cli KEYS "window_memory:*"

# Check memory
redis-cli INFO memory

# Monitor operations
redis-cli MONITOR  # (Ctrl+C to stop)
```
- [ ] Keys follow naming pattern
- [ ] Memory usage reasonable (< 10MB for dev)
- [ ] Operations show normal patterns

## Performance & Load Testing

### Setup Load Test
- [ ] Create test script with 10+ concurrent sessions
- [ ] Each session sends 5+ messages
- [ ] Monitor response times

### Performance Baseline
- [ ] Message add latency: < 5ms
- [ ] History retrieval: < 5ms  
- [ ] Response time: < 100ms (excluding LLM)
- [ ] Error rate: 0%

### Load Test Results
- [ ] All requests complete successfully
- [ ] No timeouts
- [ ] Redis memory doesn't exceed limit
- [ ] CPU usage reasonable

## Logs Review

### Check for Errors
```bash
docker-compose logs | grep ERROR    # No errors
docker-compose logs | grep CRITICAL # No critical issues
docker-compose logs rag_api | grep window_memory  # Should see log entries
```
- [ ] No ERROR level logs
- [ ] No CRITICAL level logs
- [ ] Window memory entries appear normal
- [ ] No connection refused errors

### Check for Warnings
```bash
docker-compose logs | grep WARNING  # Review any warnings
```
- [ ] Review any warnings
- [ ] Non-critical warnings acceptable
- [ ] Persistent warnings investigated

## Post-Deployment Setup

### Environment Optimization
- [ ] Adjust `WINDOW_MEMORY_SIZE` based on conversation length
- [ ] Adjust `WINDOW_MEMORY_TTL` based on session duration
- [ ] Set `LOG_LEVEL` to INFO for production
- [ ] Set `DEBUG` to false for production

### Monitoring Setup
- [ ] Redis memory monitoring configured
- [ ] API response time monitoring setup
- [ ] Error rate monitoring setup
- [ ] Session count monitoring setup

### Backup Strategy
- [ ] Redis backup configured
- [ ] Backup location documented
- [ ] Restore procedure tested
- [ ] Backup schedule set

### Documentation
- [ ] Team trained on APIs
- [ ] Troubleshooting guide shared
- [ ] Monitoring dashboard set up
- [ ] On-call procedures documented

## Sign-Off

### Technical Review
- [ ] Code reviewed for security
- [ ] No hardcoded secrets
- [ ] Error handling appropriate
- [ ] Logging levels correct
- [ ] Performance acceptable

### Functional Testing
- [ ] All test cases passed
- [ ] No known bugs
- [ ] Load testing passed
- [ ] Error scenarios handled

### Production Readiness
- [ ] Environment configured for production
- [ ] Monitoring and alerting active
- [ ] Backup procedures tested
- [ ] Incident response plan ready

### Deployment Approval
- [ ] Technical lead approved: _______________
- [ ] Date: _______________
- [ ] Notes: _______________

## First-Time Deployment Commands (Quick Copy)

```bash
# 1. Setup
cp .env.example .env
# Edit .env with your values

# 2. Build and start
docker-compose up --build -d

# 3. Verify services
docker-compose ps

# 4. Test connectivity
curl http://localhost:8080/api/chat/health

# 5. Run client test
python app/services/window_memory_client.py interactive

# 6. Check logs
docker-compose logs -f rag_api
```

## Troubleshooting During First Deployment

| Issue | Check | Fix |
|-------|-------|-----|
| Services won't start | `docker-compose logs` | Check port availability, .env settings |
| Redis connection fails | `redis-cli ping` | Restart Redis, check Redis URL |
| No messages saved | `redis-cli KEYS window_memory:*` | Check Redis connection, TTL settings |
| Slow responses | `redis-cli --latency` | Check Redis performance, network |
| OOM errors | `redis-cli INFO memory` | Reduce WINDOW_MEMORY_SIZE or TTL |

---

**Checklist Version**: 1.0
**Total Test Cases**: 13
**Expected Duration**: 30-60 minutes
**Status**: Use before first production deployment
