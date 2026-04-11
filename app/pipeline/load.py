import json
import uuid
import os
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, PayloadSchemaType

embedding_model = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
qdrant_client = QdrantClient(
    url="http://qdrant_db:6333"
)
COLLECTION_NAME = "ecommerce_products"


def setup_qdrant():
    if not qdrant_client.collection_exists(COLLECTION_NAME):
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
        print(f"✅ Đã tạo collection: {COLLECTION_NAME}")
        
        # Đánh index cho database giống hệt tư duy làm việc với MySQL/PostgreSQL
        qdrant_client.create_payload_index(COLLECTION_NAME, "price", PayloadSchemaType.FLOAT)
        qdrant_client.create_payload_index(COLLECTION_NAME, "category", PayloadSchemaType.KEYWORD)
        print("✅ Đã tạo Payload Index cho price và category.")

def embed_and_load_chunks(input_file: str, batch_size: int = 100):
    with open(input_file, "r", encoding="utf-8") as f:
        points = []
        for line in f:
            doc = json.loads(line)
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            parent_doc_id = doc.get("parent_doc_id", "unknown_parent_id")
            chunk_id = doc.get("chunk_id", str(uuid.uuid4()))

            # Tạo embedding vector
            embedding_response = embedding_model.embeddings.create(
                input=content,
                model="text-embedding-3-small"
            )
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))
            embedding_vector = embedding_response.data[0].embedding

            point = PointStruct(
                id=point_id,
                vector=embedding_vector,
                payload={
                    "parent_doc_id": parent_doc_id,
                    "chunk_id": chunk_id,
                    "content": content,
                    "metadata": metadata
                }
            )
            points.append(point)

        
            if len(points) > batch_size:
                qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=points
                )
                points = []
        if points:
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
    print(f"✅ Đã load {len(points)} chunks vào Qdrant.")

if __name__ == "__main__":
    setup_qdrant()
    input_file = "/app/data/products_data_chunks.jsonl"
    print("Starting embedding and loading process...")
    embed_and_load_chunks(input_file)
    print("Embedding and loading process completed.")