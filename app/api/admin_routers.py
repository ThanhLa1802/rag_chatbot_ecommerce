import os
from fastapi import APIRouter, HTTPException, Query
import logging
from sqlalchemy import create_engine, text
from typing import List

from app.services.sync_service import sync_product_to_vector_db
from app.schemas.product_schema import ProductUpdatePayload, ProductResponse
from app.worker import task_sync_to_qdrant

logger = logging.getLogger(__name__)
router = APIRouter()


DB_URL = os.getenv("DATABASE_URL")

# Create engine lazily to avoid import-time errors
_engine = None

def get_engine():
    """Get SQLAlchemy engine, creating it if necessary."""
    global _engine
    if _engine is None:
        if not DB_URL:
            raise RuntimeError(
                "DATABASE_URL environment variable not set. "
                "Please set it in your .env file or docker-compose environment."
            )
        _engine = create_engine(DB_URL)
    return _engine


def upsert_product_to_mysql(payload: ProductUpdatePayload):
    """
    Lưu hoặc cập nhật sản phẩm vào MySQL (Source of Truth)
    """
    upsert_query = text("""
        INSERT INTO products (product_id, name, description, category, price, status)
        VALUES (:product_id, :name, :description, :category, :price, 'active')
        ON DUPLICATE KEY UPDATE 
            name = VALUES(name),
            description = VALUES(description),
            category = VALUES(category),
            price = VALUES(price),
            updated_at = CURRENT_TIMESTAMP;
    """)
    
    engine = get_engine()
    with engine.begin() as conn: # Dùng begin() để tự động commit transaction
        conn.execute(upsert_query, {
            "product_id": payload.product_id,
            "name": payload.name,
            "description": payload.description,
            "category": payload.category,
            "price": payload.price
        })
        logger.info(f"Đã lưu thành công sản phẩm {payload.product_id} vào MySQL.")

@router.post("/product/sync", summary="Tạo/Cập nhật sản phẩm (MySQL + Vector DB)")
async def sync_product(payload: ProductUpdatePayload):
    try:
        upsert_product_to_mysql(payload)
        
        # Use Celery task to sync to Qdrant asynchronously
        task_sync_to_qdrant.delay(
            product_id=payload.product_id,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            price=payload.price
        )
        
        return {
            "status": "success", 
            "message": f"Sản phẩm {payload.product_id} đã được lưu vào MySQL và đồng bộ lên Qdrant!"
        }
    
    except Exception as e:
        logger.error(f"Lỗi API Sync: {e}")
        raise HTTPException(status_code=500, detail="Lỗi xử lý dữ liệu. Vui lòng kiểm tra log.")


@router.get("/products", response_model=List[ProductResponse], summary="Lấy danh sách tất cả sản phẩm")
async def get_all_products(
    category: str = Query(None, description="Lọc theo danh mục"),
    skip: int = Query(0, ge=0, description="Số sản phẩm bỏ qua"),
    limit: int = Query(100, ge=1, le=1000, description="Số sản phẩm lấy tối đa")
):
    """
    Lấy danh sách tất cả sản phẩm từ MySQL.
    
    Query Parameters:
    - category: Lọc theo danh mục (tùy chọn)
    - skip: Số sản phẩm bỏ qua (phân trang)
    - limit: Số sản phẩm tối đa trả về (mặc định 100)
    """
    try:
        if category:
            query = text("""
                SELECT product_id, name, description, category, price, status, updated_at
                FROM products
                WHERE category = :category
                ORDER BY updated_at DESC
                LIMIT :limit OFFSET :skip
            """)
            params = {"category": category, "skip": skip, "limit": limit}
        else:
            query = text("""
                SELECT product_id, name, description, category, price, status, updated_at
                FROM products
                ORDER BY updated_at DESC
                LIMIT :limit OFFSET :skip
            """)
            params = {"skip": skip, "limit": limit}
        
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(query, params)
            products = []
            for row in result:
                products.append({
                    "product_id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "category": row[3],
                    "price": float(row[4]),
                    "status": row[5],
                    "updated_at": row[6]
                })
        
        logger.info(f"Lấy được {len(products)} sản phẩm từ MySQL.")
        return products
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách sản phẩm: {e}")
        raise HTTPException(status_code=500, detail="Lỗi lấy dữ liệu. Vui lòng thử lại sau.")


@router.get("/products/{product_id}", response_model=ProductResponse, summary="Lấy chi tiết một sản phẩm")
async def get_product(product_id: int):
    """
    Lấy chi tiết của một sản phẩm theo ID.
    """
    try:
        query = text("""
            SELECT product_id, name, description, category, price, status, updated_at
            FROM products
            WHERE product_id = :product_id
        """)
        
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(query, {"product_id": product_id})
            row = result.first()
            
            if not row:
                raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm với ID {product_id}")
            
            product = {
                "product_id": row[0],
                "name": row[1],
                "description": row[2],
                "category": row[3],
                "price": float(row[4]),
                "status": row[5],
                "updated_at": row[6]
            }
        
        logger.info(f"Lấy chi tiết sản phẩm {product_id}.")
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi khi lấy chi tiết sản phẩm: {e}")
        raise HTTPException(status_code=500, detail="Lỗi lấy dữ liệu. Vui lòng thử lại sau.")


@router.delete("/products/{product_id}", summary="Xóa một sản phẩm")
async def delete_product(product_id: int):
    """
    Xóa một sản phẩm theo ID.
    """
    try:
        # Check if product exists
        check_query = text("SELECT product_id FROM products WHERE product_id = :product_id")
        
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(check_query, {"product_id": product_id})
            if not result.first():
                raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm với ID {product_id}")
            
            # Delete the product
            delete_query = text("DELETE FROM products WHERE product_id = :product_id")
            conn.execute(delete_query, {"product_id": product_id})
        
        logger.info(f"Đã xóa sản phẩm {product_id}.")
        return {
            "status": "success",
            "message": f"Sản phẩm {product_id} đã được xóa thành công."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi khi xóa sản phẩm: {e}")
        raise HTTPException(status_code=500, detail="Lỗi xóa dữ liệu. Vui lòng thử lại sau.")