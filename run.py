import uvicorn
from src.app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.app.main:app",
        host="localhost",
        port=settings.SERVER_PORT,
        reload=True,
        log_level="info",
    ) 