# Admin Dashboard - Product Management

## 📋 Features

### Dashboard Overview
- **Real-time Statistics**: Total products, categories, average & total price
- **Connection Status**: Live indicator showing API connection status
- **Product Count**: Real-time counter in navbar

### Product Management
- ✅ **Add Products**: Form to create new products with validation
- ✅ **Edit Products**: Click "Sửa" to modify existing products
- ✅ **Delete Products**: Remove products with confirmation
- ✅ **Search**: Real-time product search by name or category
- ✅ **Local Storage**: Auto-save to browser (backup when API unavailable)

### Responsive Design
- 📱 Mobile-friendly layout
- 💻 Desktop optimized view
- 🎨 Modern UI with gradient navbar and smooth animations

---

## 🚀 Quick Start

### Access the Dashboard
```bash
# Open in browser
file:///path/to/front_end/admin.html
# or
http://localhost:8000/front_end/admin.html  # if using local server
```

### Form Fields

| Field | Type | Required | Example |
|-------|------|----------|---------|
| Product ID | Number | Auto-generated | 1001 |
| Product Name | Text | ✅ | "Laptop Dell XPS 13" |
| Category | Select | ✅ | "Laptops" |
| Price | Number | ✅ | 999.99 |
| Description | Textarea | ✅ | "High-performance..." |

### Workflow

1. **Add a Product**
   - Click "➕ Thêm sản phẩm" button
   - Fill in all fields
   - Click "Thêm sản phẩm"
   - Product syncs to MySQL + Qdrant via Celery

2. **Edit a Product**
   - Click "✏️ Sửa" on any product row
   - Modify fields
   - Click "Cập nhật sản phẩm"

3. **Delete a Product**
   - Click "🗑️ Xóa" on any product row
   - Confirm deletion

4. **Search Products**
   - Type in search box
   - Results filter in real-time

---

## 🔄 Data Sync Flow

```
User Input (Admin Dashboard)
        ↓
Local Validation
        ↓
API Call to /api/product/sync
        ↓
┌─────────────────────────────┐
│  Backend Processing:        │
│  1. Upsert to MySQL        │
│  2. Queue Celery task      │
└─────────────────────────────┘
        ↓
Celery Worker (async)
        ↓
┌─────────────────────────────┐
│  Qdrant Sync:               │
│  - Generate embeddings      │
│  - Upsert vectors           │
│  - Index for RAG            │
└─────────────────────────────┘
```

---

## 💾 Local Data Storage

Dashboard automatically saves to browser `localStorage`:
- **Key**: `products`
- **Format**: JSON array
- **Backup**: Works offline if API unavailable
- **Sync**: Auto-syncs to backend when connection restores

### Clear Data
```javascript
// In browser console:
localStorage.removeItem('products');
location.reload();
```

---

## 🎨 Customization

### Change Categories
Edit the select options in the form:
```html
<select class="form-select" id="product-category" required>
    <option value="">-- Chọn danh mục --</option>
    <option value="Your Category">Your Category Name</option>
</select>
```

### Modify Colors
Update CSS variables at top of file:
```css
:root {
    --primary: #2563eb;        /* Main blue */
    --success: #10b981;         /* Green */
    --danger: #ef4444;          /* Red */
    --warning: #f59e0b;         /* Orange */
}
```

### Change API Endpoint
Update the configuration:
```javascript
const API_BASE = 'http://your-api-url:8080/api';
```

---

## ⚠️ Browser Support

- ✅ Chrome/Chromium (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Edge (latest)
- ⚠️ IE11: Not supported

---

## 🔗 Backend Integration

The dashboard expects these endpoints:

### POST /api/product/sync
**Sync product to MySQL + Qdrant**

Request:
```json
{
    "product_id": 1001,
    "name": "Laptop Dell XPS 13",
    "description": "High-performance ultrabook...",
    "category": "Laptops",
    "price": 999.99
}
```

Response:
```json
{
    "status": "success",
    "message": "Product synced successfully!"
}
```

---

## 📊 Statistics Panel

Real-time metrics shown in dashboard:

1. **Total Products**: Count of all products
2. **Categories**: Unique category count
3. **Average Price**: Mean product price
4. **Total Price**: Sum of all product prices

*Updates automatically on add/edit/delete*

---

## 🐛 Troubleshooting

### Problem: API Connection Shows Offline
- Check if FastAPI server is running: `docker-compose up`
- Verify DATABASE_URL environment variable
- Check browser console for CORS errors

### Problem: Products Not Showing
- Check browser's localStorage: `localStorage.getItem('products')`
- Check API response in Network tab
- Verify MySQL connection

### Problem: Changes Not Persisted to Qdrant
- Verify Redis is running: `docker ps | grep redis`
- Check Celery worker logs: `docker-compose logs celery_worker`
- Check Qdrant UI: http://localhost:6333/dashboard

---

## 📝 Example Data

```json
[
    {
        "product_id": 1001,
        "name": "Laptop Dell XPS 13",
        "category": "Laptops",
        "price": 999.99,
        "description": "Ultra-thin 13.3\" FHD display, Intel i5, 8GB RAM"
    },
    {
        "product_id": 1002,
        "name": "USB-C Hub",
        "category": "Accessories",
        "price": 49.99,
        "description": "7-in-1 USB-C hub with HDMI, USB 3.0, and SD card reader"
    }
]
```

---

## 🔐 Security Notes

⚠️ **For Development Only!**

This dashboard includes:
- No authentication (add role-based auth for production)
- No input sanitization per field (XSS protection via escapeHtml)
- No rate limiting (add backend rate limits)
- localStorage not encrypted (use secure backend storage)

For production:
- Add JWT authentication
- Implement proper RBAC
- Use HTTPS only
- Add input validation on backend
- Implement audit logging

---

## 📱 Keyboard Shortcuts

- `Enter` in search: Focus first result
- `Tab`: Navigate form fields
- `Escape`: Cancel editing (optional - implement if needed)

---

## 🎯 Future Enhancements

- [ ] Bulk import from CSV
- [ ] Product image upload
- [ ] Stock inventory tracking
- [ ] Price history chart
- [ ] Product cloning
- [ ] Category management
- [ ] Export to PDF/Excel
- [ ] Dark mode toggle
