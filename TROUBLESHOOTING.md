# Troubleshooting Guide - DATABASE_URL Error

## Error Message
```
sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from given URL string
```

This error occurs at application startup when the `DATABASE_URL` environment variable is not set or invalid.

---

## Root Cause

The application tries to create the SQLAlchemy engine at module import time. If `DATABASE_URL` is:
- ❌ Not set at all → `None`
- ❌ Empty string → `""`
- ❌ Invalid format → `"invalid-url"`

Then `create_engine()` fails with the above error.

---

## Solution

### 1. **For Docker (docker-compose)**

Ensure `DATABASE_URL` is set in your `docker-compose.yml` or `.env` file:

**Option A: Using `.env` file**

Create a `.env` file in project root:
```env
DATABASE_URL=mysql+pymysql://root:123456@mysql_db:3306/ecommerce_db
QDRANT_URL=http://qdrant_db:6333
OPENAI_API_KEY=your_key_here
```

Then run:
```bash
docker-compose up --build
```

Docker-compose will automatically load the `.env` file.

**Option B: Using docker-compose.yml directly**

Add environment variables to your `docker-compose.yml`:

```yaml
services:
  rag_api:
    environment:
      - DATABASE_URL=mysql+pymysql://root:123456@mysql_db:3306/ecommerce_db
      - QDRANT_URL=http://qdrant_db:6333
      - OPENAI_API_KEY=your_key_here
```

**Option C: Using command line**

```bash
docker-compose run \
  -e DATABASE_URL="mysql+pymysql://root:123456@mysql_db:3306/ecommerce_db" \
  rag_api
```

### 2. **For Local Development**

Create a `.env` file in the project root (or wherever you run the app):

```env
DATABASE_URL=mysql+pymysql://root:123456@localhost:3307/ecommerce_db
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=your_key_here
```

Then run the app with:
```bash
# PowerShell
$env:DATABASE_URL="mysql+pymysql://root:123456@localhost:3307/ecommerce_db"
python -m uvicorn app.main:app

# Bash
export DATABASE_URL="mysql+pymysql://root:123456@localhost:3307/ecommerce_db"
python -m uvicorn app.main:app
```

Or use python-dotenv to load from `.env`:
```python
from dotenv import load_dotenv
load_dotenv()
import os
db_url = os.getenv("DATABASE_URL")
```

---

## DATABASE_URL Format

### MySQL (with PyMySQL)
```
mysql+pymysql://username:password@host:port/database_name
```

**Example:**
```
mysql+pymysql://root:123456@localhost:3307/ecommerce_db
```

**In Docker (service name):**
```
mysql+pymysql://root:123456@mysql_db:3306/ecommerce_db
```

### MySQL (with MySQL connector)
```
mysql+mysqlconnector://username:password@host:port/database_name
```

### PostgreSQL
```
postgresql://username:password@host:port/database_name
```

### SQLite
```
sqlite:///./test.db
```

---

## Verify Connection

### 1. Test Environment Variable
```bash
# PowerShell
echo $env:DATABASE_URL

# Bash
echo $DATABASE_URL
```

### 2. Test Database Connection (Python)
```python
import os
from sqlalchemy import create_engine

db_url = os.getenv("DATABASE_URL")
print(f"DATABASE_URL: {db_url}")

engine = create_engine(db_url)
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print("Connection successful:", result.fetchone())
```

### 3. Check Docker Container Logs
```bash
docker-compose logs -f rag_api
```

Look for log messages like:
```
ERROR: DATABASE_URL environment variable not set
INFO: Successfully connected to MySQL
```

---

## Common Issues

### Issue: `pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")`

**Problem**: MySQL service not running or wrong host/port

**Solutions**:
1. Check if MySQL container is running: `docker-compose ps`
2. Verify host name in URL (docker: `mysql_db`, local: `localhost`)
3. Verify port (docker: `3306`, local: `3307`)
4. Wait for MySQL to start: `docker-compose up mysql_db` (wait 10-15 seconds)

### Issue: `2048 - Password authentication failed`

**Problem**: Wrong MySQL password

**Solutions**:
1. Check `.env` or docker-compose for MySQL credentials
2. Ensure credentials match: `MYSQL_ROOT_PASSWORD` in docker-compose
3. Example: If `MYSQL_ROOT_PASSWORD=123456`, use `mysql+pymysql://root:123456@...`

### Issue: `1044 - 'root'@'mysql_db' is not allowed to connect from host`

**Problem**: MySQL permissions or network issue

**Solutions**:
1. Restart MySQL: `docker-compose restart mysql_db`
2. Ensure services are on same network: `docker network ls`
3. Check firewall rules (for remote databases)

---

## Complete Working Example

### docker-compose.yml
```yaml
version: '3.8'

services:
  mysql_db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: 123456
      MYSQL_DATABASE: ecommerce_db
    ports:
      - "3307:3306"
    networks:
      - backend

  rag_api:
    build: .
    environment:
      - DATABASE_URL=mysql+pymysql://root:123456@mysql_db:3306/ecommerce_db
      - QDRANT_URL=http://qdrant_db:6333
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - mysql_db
    networks:
      - backend

networks:
  backend:
```

### .env
```env
OPENAI_API_KEY=sk-...your-key...
```

### Run
```bash
docker-compose up -d
```

---

## Lazy Loading Implementation

The application now uses **lazy engine initialization** to prevent import-time errors:

```python
DB_URL = os.getenv("DATABASE_URL")
_engine = None

def get_engine():
    """Get SQLAlchemy engine, creating it only when needed."""
    global _engine
    if _engine is None:
        if not DB_URL:
            raise RuntimeError("DATABASE_URL not set")
        _engine = create_engine(DB_URL)
    return _engine
```

**Benefits:**
- ✅ Environment variables can be set after import
- ✅ Better error messages
- ✅ Works with dynamic configuration
- ✅ Fails at first use, not at import time

---

## Still Having Issues?

1. **Check logs**: `docker-compose logs rag_api`
2. **Restart services**: `docker-compose restart`
3. **Rebuild images**: `docker-compose up --build`
4. **Clear volumes**: `docker-compose down -v` (⚠️ removes data!)
5. **Test MySQL directly**:
   ```bash
   docker exec -it ecommerce_mysql mysql -u root -p123456 -e "SELECT VERSION();"
   ```

---

## Reference

- SQLAlchemy URL format: https://docs.sqlalchemy.org/en/20/core/engines.html
- PyMySQL: https://pymysql.readthedocs.io/
- Docker Compose env files: https://docs.docker.com/compose/env-file/
