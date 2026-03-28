🚀 E-commerce Smart Assistant (RAG)
Trợ lý ảo Mua sắm thông minh là một hệ thống RAG (Retrieval-Augmented Generation) tiên tiến, được thiết kế để tư vấn sản phẩm và giải đáp chính sách cửa hàng một cách chính xác, thời gian thực. Hệ thống sử dụng trí tuệ nhân tạo để hiểu ngữ nghĩa câu hỏi của khách hàng, kết hợp dữ liệu sản phẩm có cấu trúc và dữ liệu chính sách không cấu trúc từ file PDF để đưa ra câu trả lời thuyết phục nhất, loại bỏ hoàn toàn hiện tượng ảo giác (hallucination).
✨ Tính năng cốt lõiSemantic Search (Tìm kiếm ngữ nghĩa): Hiểu ý định thực sự của khách hàng (ví dụ: "tai nghe tập gym" -> trả về tai nghe chống nước).Hybrid Filtering (Bộ lọc hỗn hợp): Kết hợp Vector Search với các bộ lọc cứng (giá tiền, danh mục) để đảm bảo logic kinh doanh chính xác 100%.Multi-source RAG: Trả lời kết hợp thông tin từ nguồn Sản phẩm (MySQL/Qdrant) và nguồn Chính sách (PDF).Recursive Character Chunking: Thuật toán cắt văn bản PDF thông minh, giữ nguyên ngữ cảnh của các điều khoản pháp lý.Streaming Response: Giao diện chat thời gian thực, chữ chạy ra từng từ (giống ChatGPT) giúp tăng trải nghiệm người dùng.
🏗️ Kiến trúc Hệ thốngDự án được xây dựng trên kiến trúc Microservices, đóng gói hoàn toàn bằng Docker, giúp dễ dàng triển khai và mở rộng.[Sơ đồ kiến trúc hệ thống RAG (PDF -> Vector DB -> API -> UI)]Luồng dữ liệu chính (RAG Flow):Extract (PDF ETL): Script Python trích xuất text tiếng Việt (pdfplumber), chia nhỏ (Recursive Chunking) và nhúng Vector (OpenAI) cho file chính sách PDF.Load: Dữ liệu sản phẩm (từ MySQL) và chính sách (từ PDF) được load vào Qdrant với các type khác nhau.Chat: FastAPI tiếp nhận câu hỏi -> OpenAI Embedding -> Hybrid Search trên Qdrant (tìm Vector + lọc giá/category) -> RAG Logic phân loại context -> OpenAI LLM sinh câu trả lời -> Streaming API trả về UI.
🛠️ Công nghệ sử dụngHệ thống là sự kết hợp của các công nghệ mạnh mẽ nhất trong lĩnh vực AI và Backend:MảngCông nghệVai tròCore AI / LLMOpenAI (GPT-4o-mini)"Bộ não" chịu trách nhiệm hiểu câu hỏi và sinh câu trả lời.OpenAI EmbeddingModel text-embedding-3-small biến văn bản thành Vector.Vector DatabaseQdrantLưu trữ Vector/Payload, thực hiện Hybrid Search siêu nhanh (Rust).Backend APIFastAPI (Python)Xây dựng API tốc độ cao, xử lý logic RAG và Streaming.Data ProcessingpdfplumberTrích xuất văn bản tiếng Việt chuẩn xác từ file PDF chính sách.Recursive ChunkingThuật toán cắt văn bản thông minh (custom) giữ nguyên ngữ cảnh.Relational DBMySQLNguồn dữ liệu gốc (Source of Truth) lưu trữ thông tin sản phẩm.FrontendVanilla HTML/CSS/JSGiao diện chat đơn giản, xử lý Fetch API ReadableStream.Marked.jsRender Markdown (in đậm, danh sách) trong ô chat.DevOpsDocker & Docker ComposeĐóng gói và quản lý toàn bộ hệ thống (API, DB, Qdrant).
🚀 Hướng dẫn cài đặt và chạy thử (Docker)
Yêu cầu: Máy đã cài đặt Docker và Docker Compose.
1. Clone dự ánBashgit clone https://github.com/username/ecommerce-rag-assistant.git
cd ecommerce-rag-assistant
2. Cấu hình biến môi trường (.env)Tạo file .env ở thư mục gốc và điền các thông tin sau:Đoạn mã# OpenAI API Key (Bắt buộc)
OPENAI_API_KEY=sk-your-openai-key-here

# Cấu hình Qdrant
QDRANT_URL=http://qdrant:6333
COLLECTION_NAME=ecommerce_rag

# Cấu hình MySQL
MYSQL_HOST=mysql
MYSQL_USER=user
MYSQL_PASSWORD=password
MYSQL_DATABASE=ecommerce
3. Khởi động hệ thống bằng Docker ComposeLệnh này sẽ tự động build image cho API và kéo các image cần thiết (MySQL, Qdrant).Bashdocker-compose up -d --build
4. Nạp dữ liệu (Initialization)
A. Seed dữ liệu sản phẩm (MySQL -> Qdrant)Chạy script để nạp dữ liệu sản phẩm từ MySQL vào Qdrant:Bashdocker-compose exec api python scripts/seed_products.py
B. ETL dữ liệu chính sách (PDF -> Qdrant)Copy file PDF chính sách vào thư mục data/ và chạy script ETL:Bash# Giả sử file là data/chinh_sach.pdf
docker-compose exec api python scripts/etl_pdf.py --file data/chinh_sach.pdf
5. Truy cập
Giao diện Chat: Mở trình duyệt và truy cập http://localhost:8080Qdrant Dashboard: Truy cập http://localhost:6333/dashboard để kiểm tra dữ liệu Vector.API Documentation (Swagger): Truy cập http://localhost:8080/docs📖 Cấu trúc thư mụcPlaintext.
├── app/                  # Mã nguồn FastAPI
│   ├── api/              # Định nghĩa các routes (endpoints)
│   ├── core/             # Cấu hình hệ thống (config, security)
│   ├── models/           # SQLAlchemy models (MySQL)
│   ├── schemas/          # Pydantic schemas (Request/Response)
│   └── services/         # Logic xử lý chính (RAG, OpenAI, Qdrant)
├── data/                 # Thư mục chứa các file PDF chính sách
├── docker/               # Các file cấu hình Docker (Dockerfile, etc.)
├── scripts/              # Các script ETL và Seed dữ liệu
├── static/               # Frontend (HTML, CSS, JS)
├── .env.example          # File ví dụ cấu hình biến môi trường
├── docker-compose.yml    # File cấu hình Docker Compose
├── requirements.txt      # Các thư viện Python cần thiết
└── README.md             # File này
🤝 Đóng góp
Mọi đóng góp (Pull Request) đều được hoan nghênh. Vui lòng mở Issue trước để thảo luận về những thay đổi bạn muốn thực hiện.
📄 Giấy phép
Dự án này được phát hành dưới Giấy phép MIT. Xem file LICENSE để biết thêm chi tiết.