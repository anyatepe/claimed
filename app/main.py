"""
Example FastAPI application main file.
Include this router in your main FastAPI app.
"""
from fastapi import FastAPI
from app.api.routes.chat import router as chat_router

app = FastAPI(title="Chat API", version="1.0.0")

# Include the chat router
app.include_router(chat_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
