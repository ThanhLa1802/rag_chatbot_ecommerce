# E-Commerce RAG Pipeline with Window Memory

Complete, production-ready Retrieval-Augmented Generation (RAG) system for e-commerce with stateful conversation tree tracking using Redis-based sliding window memory.

## ✨ Features

- **Stateful Conversations**: Multi-turn conversations with full context retention
- **RAG Integration**: Vector search on Qdrant with semantic similarity
- **Admin Dashboard**: Beautiful UI for product management and stats
- **Async Processing**: Celery workers for background tasks
- **Containerized**: Full Docker setup with all services
- **Production-Ready**: Error handling, logging, monitoring

## 🏗️ Architecture

```
Frontend (HTML)     Admin Dashboard
     ↓                   ↓
FastAPI Server ← Conversation Memory ← Redis
     ↓                               ← MySQL
     ↓                               ← Qdrant
LLM Services
(OpenAI)            Celery Worker
```

## 📁 Project Structure

```
├── app/
│   ├── main.py                    # FastAPI app entry point
│   ├── api/
│   │   ├── chat_routers.py       # Chat endpoints with window memory
│   │   └── admin_routers.py      # Product management API
│   ├── pipeline/
│   │   ├── extract.py            # Data extraction
│   │   ├── load.py               # Data loading
│   │   ├── transform.py          # Data transformation
│   │   └── runner.py             # Pipeline orchestration
│   ├── schemas/
│   │   ├── chat_schema.py        # Request/response models
│   │   └── product_schema.py     # Product models
│   └── services/
│       ├── window_memory.py      # ✨ Window Memory Manager
│       ├── window_memory_client.py # Testing client
│       ├── rag_service.py        # RAG generation engine
│       └── sync_service.py       # Data sync service
├── front_end/
│   ├── index.html                # Admin dashboard
│   └── admin.html                # Product management UI
├── data/
│   ├── init.sql                  # Database initialization
│   └── test_*.jsonl              # Sample data
├── docker-compose.yml            # Service orchestration
├── Dockerfile                    # App container
├── requirements.txt              # Python dependencies
│
├── WINDOW_MEMORY_IMPLEMENTATION.md  # ✨ Complete implementation guide
├── WINDOW_MEMORY.md                 # System documentation
├── DEPLOYMENT_GUIDE.md              # Deployment procedures
├── DEPLOYMENT_CHECKLIST.md          # First-time setup checklist
├── QUICK_REFERENCE.md               # Developer quick reference
├── API_ENDPOINTS.md                 # API documentation
├── ADMIN_DASHBOARD.md               # Dashboard guide
├── TROUBLESHOOTING.md               # Troubleshooting guide
├── REDIS_SETUP.md                   # Redis configuration
├── .env.example                     # Environment template
└── README.md                        # This file
```

## 🚀 Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.9+ (for local development)
- OpenAI API key
- 2GB+ free memory

### 2. Setup

```bash
# Clone repository
git clone <repo-url>
cd rag_pipeline

# Copy environment template
cp .env.example .env

# IMPORTANT: Edit .env and set:
# - OPENAI_API_KEY
# - DATABASE_URL (if using external MySQL)
# - Other services as needed
```

### 3. Start Services

```bash
# Build and start all services
docker-compose up --build

# Or in background
docker-compose up --build -d

# View logs
docker-compose logs -f rag_api
```

### 4. Test

```bash
# Access API docs
curl http://localhost:8080/docs

# Check health
curl http://localhost:8080/api/chat/health

# Test chat with memory
SESSION_ID=$(uuidgen)
curl -X POST "http://localhost:8080/api/chat?session_id=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello!"}'

# View conversation history
curl "http://localhost:8080/api/chat/history/$SESSION_ID"
```

## 📚 Documentation

### For First-Time Setup
1. **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Step-by-step first deployment with validation tests
2. **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete setup, testing, and troubleshooting guide

### For Development
3. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Common tasks and code snippets
4. **[WINDOW_MEMORY_IMPLEMENTATION.md](WINDOW_MEMORY_IMPLEMENTATION.md)** - Full implementation details
5. **[API_ENDPOINTS.md](API_ENDPOINTS.md)** - REST API reference

### For Understanding the System
6. **[WINDOW_MEMORY.md](WINDOW_MEMORY.md)** - Window Memory system architecture and usage
7. **[ADMIN_DASHBOARD.md](ADMIN_DASHBOARD.md)** - Admin UI features and usage
8. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

### For Operations
9. **[REDIS_SETUP.md](REDIS_SETUP.md)** - Redis configuration and management
10. **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Production deployment and monitoring

## 🎯 Window Memory Features

The system tracks conversations using **sliding window memory**:

```python
# Store user message
window_memory.add_message(
    session_id="user-123",
    message="Show me laptops under 30 million",
    role="user"
)

# Later, retrieve full context
context = window_memory.get_context_summary("user-123")
# === Conversation History ===
# [USER @ 10:30:45]
# Show me laptops under 30 million

# Auto-expanded context sent to LLM
response = generate_answer(context + current_query)

# Store assistant response
window_memory.add_message(session_id, response, "assistant")
```

### Key Capabilities
- ✅ Session-based conversation tracking
- ✅ Automatic context window management
- ✅ Redis-backed distributed storage
- ✅ Sliding window (keeps last N messages)
- ✅ Auto-expiration (TTL-based cleanup)
- ✅ Session statistics & monitoring
- ✅ Multi-user isolation

## 🔧 Configuration

### Core Settings

```bash
# .env file
# Window Memory
WINDOW_MEMORY_SIZE=5              # Messages to keep per session
WINDOW_MEMORY_TTL=3600            # Session lifetime (seconds)
REDIS_URL=redis://redis:6379/0

# Services
OPENAI_API_KEY=sk-...
QDRANT_URL=http://qdrant_db:6333
DATABASE_URL=mysql+pymysql://root:password@mysql_db:3306/ecommerce
DEBUG=false
LOG_LEVEL=INFO
```

### Optimization

```bash
# Development (large window, verbose logging)
WINDOW_MEMORY_SIZE=20
WINDOW_MEMORY_TTL=7200
LOG_LEVEL=DEBUG

# Production (optimized performance)
WINDOW_MEMORY_SIZE=5
WINDOW_MEMORY_TTL=1800
LOG_LEVEL=INFO
```

## 📊 API Endpoints

### Chat with Window Memory
- **POST** `/api/chat?session_id=SESSION_ID` - Send message with context
- **GET** `/api/chat/history/{session_id}` - Retrieve conversation
- **DELETE** `/api/chat/history/{session_id}` - Clear session
- **GET** `/api/chat/health` - Check system health

### Product Management
- **GET** `/api/products` - List all products
- **GET** `/api/products/{id}` - Get product details
- **POST** `/api/product/sync` - Add/update product
- **DELETE** `/api/products/{id}` - Remove product

### System
- **GET** `/docs` - Interactive API documentation (Swagger)
- **GET** `/` - Health check

## 🖥️ Admin Dashboard

Access the admin dashboard at:
```
file:///path/to/front_end/admin.html
```

Features:
- View all products with Vietnamese currency formatting (₫)
- Add/edit product details
- Delete products
- Real-time connection status
- Product statistics and categories

## 🐳 Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| **rag_api** | 8080 | FastAPI application |
| **mysql_db** | 3307 | Product database |
| **qdrant_db** | 6333 | Vector embeddings storage |
| **redis** | 6379 | Session & memory storage |
| **celery_worker** | N/A | Background tasks |

## 📝 Testing

### Unit Tests
```bash
python -m pytest app/tests/
```

### Integration Tests
```bash
python app/services/window_memory_client.py interactive
```

### Load Tests
```bash
python app/services/window_memory_client.py batch
```

## 🔍 Monitoring

### Redis Connections
```bash
redis-cli
> KEYS "window_memory:*"
> HGETALL "window_memory:meta:SESSION_ID"
> TTL "window_memory:session:SESSION_ID"
```

### Service Logs
```bash
# API logs
docker-compose logs -f rag_api

# Redis logs
docker-compose logs -f redis

# Celery worker logs
docker-compose logs -f celery_worker
```

### Health Check
```bash
curl http://localhost:8080/api/chat/health
```

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| Redis connection refused | Start Redis: `docker-compose restart redis` |
| API won't start | Check `.env` settings, verify ports available |
| Messages not persisting | Ensure same `session_id` used, check Redis TTL |
| Slow responses | Check Qdrant/OpenAI connectivity, monitor Redis |

## 📖 Full Documentation Index

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [WINDOW_MEMORY_IMPLEMENTATION.md](WINDOW_MEMORY_IMPLEMENTATION.md) | Complete implementation overview | 10 min |
| [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) | First deployment validation | 45 min |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Detailed deployment & testing | 20 min |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Common tasks & code examples | 5 min |
| [WINDOW_MEMORY.md](WINDOW_MEMORY.md) | System architecture | 15 min |
| [API_ENDPOINTS.md](API_ENDPOINTS.md) | REST API reference | 10 min |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Problem solving guide | 10 min |

## 🏆 What's Implemented

- ✅ Window Memory system with Redis backend
- ✅ Stateful chat endpoints with session tracking
- ✅ Admin dashboard with VND currency formatting
- ✅ Product CRUD operations
- ✅ CORS support with preflight handling
- ✅ Async streaming responses
- ✅ Error handling and logging
- ✅ Docker containerization
- ✅ Comprehensive documentation
- ✅ Python testing client

## 🔮 Roadmap

- [ ] Authentication/Authorization
- [ ] Message compression for large windows
- [ ] Redis Cluster support
- [ ] GraphQL playground
- [ ] Advanced analytics dashboard
- [ ] Message retention policies
- [ ] Distributed tracing
- [ ] Performance optimization caching layer

## 📞 Support & Troubleshooting

**For setup issues**: See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
**For API questions**: See [API_ENDPOINTS.md](API_ENDPOINTS.md)
**For Window Memory help**: See [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
**For problems**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## 📄 License

This project is provided as-is for educational and commercial use.

## 🙏 Acknowledgments

Built with:
- FastAPI for REST APIs
- Redis for distributed memory storage
- Qdrant for vector databases
- OpenAI for LLM capabilities
- Docker for containerization
- SQLAlchemy for database ORM

---

**Version**: 1.0  
**Last Updated**: 2024-01-15  
**Status**: ✅ Production Ready

**Quick Links:**
- [Start Deployment](DEPLOYMENT_CHECKLIST.md) - Begin here for first-time setup
- [API Docs](http://localhost:8080/docs) - Interactive API (when running)
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues
- [Admin Dashboard](front_end/admin.html) - Product management UI
