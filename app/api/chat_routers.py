from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import logging
from datetime import datetime
import uuid

# Import hàm sinh câu trả lời từ tầng Service mà ta vừa viết
from app.services.rag_service import generate_answer_stream, analyze_user_query
from app.services.window_memory import get_window_memory
from app.schemas.chat_schema import ChatRequest

logger = logging.getLogger(__name__)

# Initialize window memory
window_memory = get_window_memory()

# init router
router = APIRouter()

@router.options("/chat", summary="CORS preflight for chat endpoint")
async def options_chat():
    """Handle CORS preflight requests."""
    return {"status": "ok"}

@router.post("/chat", summary="Chat với Trợ lý ảo E-commerce")
async def chat_with_bot(
    request: ChatRequest,
    session_id: str = Query(default=None, description="Unique session ID for conversation memory (auto-generated if not provided)")
):
    """
    Endpoint nhận câu hỏi và trả về câu trả lời dạng Stream (SSE).
    Hỗ trợ lọc trước theo danh mục và giá tiền để tăng độ chính xác.
    Sử dụng Window Memory để theo dõi lịch sử hội thoại.
    """
    try:
        # Generate session_id if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Store user message in window memory
        window_memory.add_message(
            session_id=session_id,
            message=request.query,
            role="user",
            metadata={"query_received_at": str(datetime.now())}
        )
        
        # Get conversation context from window memory
        conversation_history = window_memory.get_context_summary(session_id)
        logger.info(f"Session {session_id}: User query received. History window has {len(window_memory.get_conversation_window(session_id))} messages")
        
        filters = analyze_user_query(request.query)
        
        # Create enhanced prompt with conversation context
        enhanced_prompt = f"""Conversation Context:
                {conversation_history}
                Current Query: {request.query}
                Vui lòng trả lời dựa trên ngữ cảnh hội thoại và áp dụng các bộ lọc"""
        
        answer_generator = generate_answer_stream(
            query=enhanced_prompt,
            category=filters.get("category"),
            max_price=filters.get("max_price")
        )
        
        # Generator wrapper to capture response and store in memory
        async def response_generator():
            full_response = ""
            try:
                # Convert sync generator to async
                for chunk in answer_generator:
                    full_response += chunk
                    yield chunk
                
                # Store assistant response in window memory
                window_memory.add_message(
                    session_id=session_id,
                    message=full_response,
                    role="assistant",
                    metadata={"response_completed_at": str(datetime.now())}
                )
                logger.info(f"Session {session_id}: Assistant response stored in window memory")
                
            except Exception as e:
                logger.error(f"Error in response generator: {e}")
                raise
        
        return StreamingResponse(
            response_generator(), 
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"❌ Lỗi tại endpoint /chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Lỗi hệ thống nội bộ. Vui lòng thử lại sau.")


@router.get("/chat/history/{session_id}", summary="Get conversation history for a session")
async def get_chat_history(session_id: str):
    """
    Retrieve conversation history for a specific session from window memory.
    """
    try:
        messages = window_memory.get_conversation_window(session_id)
        stats = window_memory.get_session_stats(session_id)
        
        return {
            "session_id": session_id,
            "messages": messages,
            "statistics": stats.get("statistics", {}),
            "message_count": len(messages)
        }
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving chat history")


@router.delete("/chat/history/{session_id}", summary="Clear conversation history for a session")
async def clear_chat_history(session_id: str):
    """
    Clear all conversation history for a specific session.
    """
    try:
        success = window_memory.clear_session(session_id)
        if success:
            return {"status": "success", "message": f"Session {session_id} cleared"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear session")
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(status_code=500, detail="Error clearing chat history")


@router.get("/chat/health", summary="Check window memory health")
async def check_window_memory_health():
    """Check the health of the window memory service."""
    try:
        is_healthy = window_memory.health_check()
        active_sessions = len(window_memory.get_all_sessions())
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "redis_connected": is_healthy,
            "active_sessions": active_sessions
        }
    except Exception as e:
        logger.error(f"Error checking window memory health: {e}")
        raise HTTPException(status_code=500, detail="Error checking health")