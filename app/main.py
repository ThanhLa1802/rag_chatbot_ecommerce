from fastapi import FastAPI
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Rag chatbot",
    description="Chat bot hỗ trẹo tìm kiếm sản phẩm",
    version="1.0.0"
)


@app.get("/")
def test():
    return {
        "status": "online",
        "message": "Welcome to my chatbot"
    }

logger.info("Run server FastAPI")