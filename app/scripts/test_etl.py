import json
import os
import uuid
import pdfplumber
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Cấu hình
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
qdrant = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant_db:6333"))
COLLECTION_NAME = "ecommerce_products"

def split_text_recursive(text, max_length=800, overlap=100):
    """
    Hàm Transform nâng cao: Cắt văn bản theo thứ tự ưu tiên: 
    Dấu chấm -> Dấu cách -> Ký tự.
    """
    # Các ký tự ưu tiên để cắt
    separators = ["\n\n", "\n", ". ", " ", ""]
    
    final_chunks = []
    
    # Logic đơn giản hóa của RecursiveCharacterTextSplitter
    def recursive_split(content, seps):
        if len(content) <= max_length:
            return [content]
        
        current_sep = seps[0] if seps else ""
        if current_sep:
            splits = content.split(current_sep)
        else:
            # Nếu không còn dấu ngăn cách nào, cắt cứng theo độ dài
            return [content[i:i+max_length] for i in range(0, len(content), max_length)]
            
        chunks = []
        current_doc = ""
        
        for s in splits:
            # Nếu thêm đoạn mới vào vẫn chưa quá giới hạn
            if len(current_doc) + len(s) + len(current_sep) <= max_length:
                current_doc += (current_sep if current_doc else "") + s
            else:
                # Lưu đoạn cũ và bắt đầu đoạn mới
                if current_doc:
                    chunks.append(current_doc)
                # Đệ quy cho phần còn lại nếu phần đó vẫn quá dài
                chunks.extend(recursive_split(s, seps[1:]))
                current_doc = s
        
        if current_doc:
            chunks.append(current_doc)
        return chunks

    return recursive_split(text, separators)

def etl_pdf_to_qdrant(pdf_path):
    print(f"🚀 Bắt đầu ETL cho file: {pdf_path}")
    
    # --- STEP 1: EXTRACT ---
    reader = pdfplumber.open(pdf_path)
    all_points = []
    
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if not text: continue
        
        # --- STEP 2: TRANSFORM ---
        chunks = split_text_recursive(text, max_length=800, overlap=100)
        for i, chunk in enumerate(chunks):
            doc_id = f"pdf_{page_num}_{i}"
            # Gắn thêm context để AI biết đây là chính sách
            content_to_embed = f"[CHÍNH SÁCH CỬA HÀNG] Trang {page_num}: {chunk}"
            
            # Gọi OpenAI Embedding
            embed_res = client.embeddings.create(
                input=content_to_embed,
                model="text-embedding-3-small"
            )
            vector = embed_res.data[0].embedding
            
            # Đóng gói Payload (Quan trọng: price=0, category='chinh_sach')
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id))
            all_points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "chunk_id": doc_id,
                        "content": content_to_embed,
                        "parent_doc_id": "chinh_sach_doi_tra",
                        "category": "chinh_sach",
                        "price": 0, # Mặc định để không bị filter giá loại bỏ
                        "type": "policy"
                    }
                )
            )

    # --- STEP 3: LOAD ---
    if all_points:
        qdrant.upsert(collection_name=COLLECTION_NAME, points=all_points)
        print(f"✅ Đã LOAD thành công {len(all_points)} đoạn chính sách vào Qdrant!")

if __name__ == "__main__":
    # Thay tên file PDF bạn vừa tạo vào đây
    etl_pdf_to_qdrant("/app/data/chinh_sach_cua_hang.pdf")