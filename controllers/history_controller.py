from fastapi import APIRouter
from data_processing.chat_memory import memory

router = APIRouter()

@router.get("/history/{user_id}")
async def get_history(user_id: str):
    return {"user_id": user_id, "history": memory.get_history(user_id)}

@router.delete("/history/{user_id}")
async def clear_history(user_id: str):
    memory.reset(user_id)
    return {"message": f"Đã xóa lịch sử của {user_id}."}
