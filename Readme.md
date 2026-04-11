# 🚀 E-commerce Smart Assistant (RAG)

Trợ lý ảo Mua sắm thông minh là một hệ thống **RAG (Retrieval-Augmented Generation)** tiên tiến, được thiết kế để:

- Tư vấn sản phẩm  
- Giải đáp chính sách cửa hàng một cách chính xác, theo thời gian thực  

Hệ thống sử dụng AI để:
- Hiểu ngữ nghĩa câu hỏi khách hàng  
- Kết hợp dữ liệu **có cấu trúc (product)** và **không cấu trúc (PDF policy)**  
- Đưa ra câu trả lời chính xác, hạn chế hoàn toàn hiện tượng *hallucination*

---

## ✨ Tính năng cốt lõi

### 🔍 Semantic Search (Tìm kiếm ngữ nghĩa)
Hiểu đúng ý định người dùng  
> Ví dụ: *"tai nghe tập gym"* → trả về tai nghe chống nước

### ⚙️ Hybrid Filtering (Bộ lọc hỗn hợp)
Kết hợp:
- Vector Search  
- Filter cứng (giá, category)  

→ Đảm bảo logic business chính xác 100%

### 🔗 Multi-source RAG
Trả lời dựa trên nhiều nguồn:
- 📦 Product (MySQL / Qdrant)  
- 📄 Policy (PDF)

### ✂️ Recursive Character Chunking
- Cắt nhỏ văn bản PDF thông minh  
- Giữ nguyên context

### ⚡ Streaming Response
- Trả về kết quả dạng streaming (giống ChatGPT)  
- Tăng trải nghiệm người dùng (UX)

---

## 🏗️ Kiến trúc hệ thống

Dự án sử dụng kiến trúc **Microservices**, đóng gói bằng **Docker**:
[PDF] → [ETL] → [Vector DB (Qdrant)]
↓
[API - FastAPI]
↓
[UI]


---

## 🔄 Main Data Flow (RAG Pipeline)

### 1. Extract (ETL)
- Use `pdfplumber` to extract Vietnamese text from PDF policies
- Apply recursive chunking to split documents while preserving context
- Generate embeddings using OpenAI API

### 2. Load
- Product data: Loaded from MySQL
- Policy data: Loaded from PDF
- Store both types in Qdrant (vector database) with appropriate tags

### 3. Chat Flow

```mermaid
flowchart LR
    A[User Question] --> B[FastAPI API Layer]
    B --> C[OpenAI Embedding Generation]
    C --> D[Qdrant Hybrid Search]
    D --> E[RAG Logic & Context Assembly]
    E --> F[OpenAI LLM Generation]
    F --> G[Streaming Response to UI]