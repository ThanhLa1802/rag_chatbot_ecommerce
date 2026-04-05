# Product Management API Endpoints

## Base URL
```
http://localhost:8080/api
```

---

## 📋 Endpoints

### 1. **POST /product/sync** - Create or Update Product
Syncs product to MySQL and queues async sync to Qdrant vector database.

**Request:**
```http
POST /api/product/sync
Content-Type: application/json

{
    "product_id": 1001,
    "name": "Laptop Dell XPS 13",
    "description": "Ultra-thin 13.3\" FHD display, Intel i5, 8GB RAM",
    "category": "Laptops",
    "price": 999.99
}
```

**Response (200 OK):**
```json
{
    "status": "success",
    "message": "Sản phẩm 1001 đã được lưu vào MySQL và đồng bộ lên Qdrant!"
}
```

**Error Response (500):**
```json
{
    "detail": "Lỗi xử lý dữ liệu. Vui lòng kiểm tra log."
}
```

---

### 2. **GET /products** - Get All Products
Retrieves all products from MySQL with optional filtering and pagination.

**Request:**
```http
GET /api/products?category=Laptops&skip=0&limit=20
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | No | Filter by category |
| `skip` | integer | No | Number of products to skip (default: 0) |
| `limit` | integer | No | Max products to return (default: 100, max: 1000) |

**Response (200 OK):**
```json
[
    {
        "product_id": 1001,
        "name": "Laptop Dell XPS 13",
        "description": "Ultra-thin 13.3\" FHD display, Intel i5, 8GB RAM",
        "category": "Laptops",
        "price": 999.99,
        "status": "active",
        "updated_at": "2026-04-05T10:30:45"
    },
    {
        "product_id": 1002,
        "name": "USB-C Hub",
        "description": "7-in-1 USB-C hub with HDMI, USB 3.0, and SD card reader",
        "category": "Accessories",
        "price": 49.99,
        "status": "active",
        "updated_at": "2026-04-05T09:15:20"
    }
]
```

**Examples:**

Get all products:
```bash
curl http://localhost:8080/api/products
```

Get first 10 products:
```bash
curl "http://localhost:8080/api/products?limit=10"
```

Get products by category:
```bash
curl "http://localhost:8080/api/products?category=Laptops"
```

Pagination - Get next 10 products:
```bash
curl "http://localhost:8080/api/products?limit=10&skip=10"
```

---

### 3. **GET /products/{product_id}** - Get Single Product
Retrieves a specific product by ID.

**Request:**
```http
GET /api/products/1001
```

**Response (200 OK):**
```json
{
    "product_id": 1001,
    "name": "Laptop Dell XPS 13",
    "description": "Ultra-thin 13.3\" FHD display, Intel i5, 8GB RAM",
    "category": "Laptops",
    "price": 999.99,
    "status": "active",
    "updated_at": "2026-04-05T10:30:45"
}
```

**Error Response (404):**
```json
{
    "detail": "Không tìm thấy sản phẩm với ID 1001"
}
```

**Example:**
```bash
curl http://localhost:8080/api/products/1001
```

---

### 4. **DELETE /products/{product_id}** - Delete Product
Removes a product from MySQL. Also needs manual cleanup from Qdrant.

**Request:**
```http
DELETE /api/products/1001
```

**Response (200 OK):**
```json
{
    "status": "success",
    "message": "Sản phẩm 1001 đã được xóa thành công."
}
```

**Error Response (404):**
```json
{
    "detail": "Không tìm thấy sản phẩm với ID 1001"
}
```

**Error Response (500):**
```json
{
    "detail": "Lỗi xóa dữ liệu. Vui lòng thử lại sau."
}
```

**Example:**
```bash
curl -X DELETE http://localhost:8080/api/products/1001
```

---

## 🔄 Data Flow

### Creating/Updating a Product

```
POST /api/product/sync
        ↓
Validate input
        ↓
Upsert to MySQL
(Source of Truth)
        ↓
Queue Celery task
        ↓
Return success response
        ↓
[Async - Celery Worker]
        ↓
Generate embeddings
        ↓
Upsert to Qdrant
(Vector store for RAG)
```

### Retrieving Products

```
GET /api/products?category=X&skip=0&limit=20
        ↓
Query MySQL with filters
        ↓
Return JSON response
(No Qdrant lookup needed)
```

---

## 📊 Response Models

### ProductResponse
```python
{
    "product_id": int,           # Unique identifier
    "name": str,                 # Product name
    "description": str,          # Product description
    "category": str,             # Product category
    "price": float,              # Price in USD
    "status": str,               # "active" or "inactive"
    "updated_at": datetime       # ISO 8601 timestamp
}
```

### SyncResponse
```python
{
    "status": str,               # "success" or error status
    "message": str               # Human-readable message
}
```

### ErrorResponse
```python
{
    "detail": str                # Error description
}
```

---

## 🔐 Error Handling

### Common HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Product fetched/updated/deleted |
| 404 | Not Found | Product ID doesn't exist |
| 500 | Server Error | Database connection failed |
| 422 | Validation Error | Invalid input data |

### Error Examples

**Missing required field:**
```json
{
    "detail": [
        {
            "loc": ["body", "name"],
            "msg": "field required",
            "type": "value_error.missing"
        }
    ]
}
```

**Invalid price:**
```json
{
    "detail": [
        {
            "loc": ["body", "price"],
            "msg": "ensure this value is greater than 0",
            "type": "value_error.number.not_gt",
            "ctx": {"limit_value": 0}
        }
    ]
}
```

---

## 🧪 Testing with cURL

### Create a product:
```bash
curl -X POST http://localhost:8080/api/product/sync \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1001,
    "name": "Laptop Dell XPS 13",
    "description": "Ultra-thin laptop",
    "category": "Laptops",
    "price": 999.99
  }'
```

### Get all products:
```bash
curl http://localhost:8080/api/products
```

### Get product by ID:
```bash
curl http://localhost:8080/api/products/1001
```

### Delete product:
```bash
curl -X DELETE http://localhost:8080/api/products/1001
```

### Filter by category:
```bash
curl "http://localhost:8080/api/products?category=Laptops"
```

---

## 🧪 Testing with Python

```python
import requests

API_BASE = "http://localhost:8080/api"

# Create product
product = {
    "product_id": 1001,
    "name": "Laptop Dell XPS 13",
    "description": "Ultra-thin laptop",
    "category": "Laptops",
    "price": 999.99
}
response = requests.post(f"{API_BASE}/product/sync", json=product)
print(response.json())

# Get all products
response = requests.get(f"{API_BASE}/products")
products = response.json()
print(f"Total products: {len(products)}")

# Get by category
response = requests.get(f"{API_BASE}/products?category=Laptops")
laptops = response.json()
print(f"Laptops found: {len(laptops)}")

# Get single product
response = requests.get(f"{API_BASE}/products/1001")
product = response.json()
print(product)

# Delete product
response = requests.delete(f"{API_BASE}/products/1001")
print(response.json())
```

---

## 🧪 Testing with JavaScript

```javascript
const API_BASE = "http://localhost:8080/api";

// Create product
async function createProduct() {
    const product = {
        product_id: 1001,
        name: "Laptop Dell XPS 13",
        description: "Ultra-thin laptop",
        category: "Laptops",
        price: 999.99
    };
    
    const response = await fetch(`${API_BASE}/product/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(product)
    });
    
    const result = await response.json();
    console.log(result);
}

// Get all products
async function getAllProducts() {
    const response = await fetch(`${API_BASE}/products`);
    const products = await response.json();
    console.log(products);
}

// Get by category
async function getByCategory(category) {
    const response = await fetch(`${API_BASE}/products?category=${category}`);
    const products = await response.json();
    console.log(products);
}

// Get single product
async function getProduct(productId) {
    const response = await fetch(`${API_BASE}/products/${productId}`);
    const product = await response.json();
    console.log(product);
}

// Delete product
async function deleteProduct(productId) {
    const response = await fetch(`${API_BASE}/products/${productId}`, {
        method: 'DELETE'
    });
    const result = await response.json();
    console.log(result);
}
```

---

## 📈 Performance Considerations

### Pagination
- For large datasets, always use `limit` and `skip` to avoid loading too much data
- Recommended: `limit=20` to `limit=100` per request
- Example: Get second page with 20 items: `?skip=20&limit=20`

### Filtering
- Filter by `category` on database side (more efficient)
- Always specify `category` if you only need specific categories
- Reduces data transfer and API response time

### Caching
- Response from `/products` endpoint is safe to cache client-side
- Invalidate cache on add/update/delete operations
- Admin dashboard automatically handles this via localStorage

---

## 🔄 Integration with Admin Dashboard

The admin dashboard at `front_end/admin.html` automatically:

1. **On Load**: Fetches all products from `/api/products`
2. **On Create**: Calls `POST /api/product/sync`
3. **On Update**: Calls `POST /api/product/sync` (upsert)
4. **On Delete**: Calls `DELETE /api/products/{product_id}`
5. **Fallback**: Uses localStorage if API is unavailable

---

## 📝 Logging

All endpoints log their actions to the application logs:

```
INFO - Lấy được 5 sản phẩm từ MySQL.
INFO - Lấy chi tiết sản phẩm 1001.
INFO - Đã xóa sản phẩm 1001.
INFO - Đã lưu thành công sản phẩm 1001 vào MySQL.
```

View logs with: `docker-compose logs rag_api`

---

## 🚀 Next Steps

1. Add authentication/authorization
2. Add rate limiting per user
3. Add sorting options (by name, price, date)
4. Add bulk operations (delete multiple)
5. Add export functionality (CSV, PDF)
6. Add product image upload
7. Add inventory tracking
