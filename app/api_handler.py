import uvicorn
from aws_lambda_powertools.logging import Logger
from fastapi import FastAPI
from mangum import Mangum

from app import settings
from app.api.v1.api import router as api_v1_router

logger = Logger()

app = FastAPI(debug=settings.debug, title="Users Service API", version="1.0.0")
app.include_router(api_v1_router)

handler = Mangum(app)
handler = logger.inject_lambda_context(handler)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8080, reload=True)
