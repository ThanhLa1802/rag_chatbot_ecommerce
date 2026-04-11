import json
from langchain_text_splitters import RecursiveCharacterTextSplitter

def transform_jsonl_to_chunks(input_file: str, output_file: str, chunk_size: int = 500, chunk_overlap: int = 50):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    processed_trunks = set()
    with open(input_file, "r", encoding="utf-8") as infile, open(output_file, "w", encoding="utf-8") as outfile:
        for line in infile:
            doc = json.loads(line)
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            doc_id = doc.get("doc_id", "unknown_id")

            # Split content into chunks
            chunks = text_splitter.split_text(content)

            for i, chunk in enumerate(chunks):
                if metadata.get("type") == "product_info":
                    enriched_text = f"[Thuộc sản phẩm id {doc_id}] {chunk}"
                else:
                    enriched_text = chunk
                chunk_doc = {
                    "parent_doc_id": doc_id,
                    "chunk_id": f"{doc_id}_chunk_{i}",
                    "content": enriched_text,
                    "metadata": metadata
                }
                processed_trunks.add(json.dumps(chunk_doc, ensure_ascii=False))
    with open(output_file, "a", encoding="utf-8") as outfile:
        for chunk in processed_trunks:
            outfile.write(chunk + "\n")
    print(f"Transformation completed. Output file: {output_file}")

if __name__ == "__main__":
    input_file = "/app/data/products_data_raws.jsonl"
    output_file = "/app/data/products_data_chunks.jsonl"
    transform_jsonl_to_chunks(input_file, output_file)