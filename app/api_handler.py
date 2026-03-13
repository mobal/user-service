import uvicorn
from aws_lambda_powertools.logging import Logger
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from starlette.middleware.exceptions import ExceptionMiddleware

from app import settings
from app.api.v1.api import router as api_v1_router
from app.middlewares import CorrelationIdMiddleware
from app.models.response.error import ErrorResponse, ValidationErrorResponse

logger = Logger()

app = FastAPI(debug=settings.debug, title="Users Service API", version="1.0.0")
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(GZipMiddleware)
app.add_middleware(ExceptionMiddleware, handlers=app.exception_handlers)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
app.include_router(api_v1_router)

handler = Mangum(app)
handler = logger.inject_lambda_context(handler)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.exception_handler(Exception)
def botocore_error_handler(request: Request, error: Exception) -> JSONResponse:
    logger.exception(error)
    error_message = str(error) if settings.debug else "Internal Server Error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(
        content=ErrorResponse(status=status_code, error=error_message).model_dump(
            by_alias=True
        ),
        status_code=status_code,
    )


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
    logger.exception(error)

    return JSONResponse(
        content=ErrorResponse(status=error.status_code, error=error.detail).model_dump(
            by_alias=True
        ),
        status_code=error.status_code,
    )


@app.exception_handler(RequestValidationError)
def request_validation_error_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    logger.exception(error)
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT

    return JSONResponse(
        content=ValidationErrorResponse(
            status=status_code,
            error="Validation Error",
            errors=jsonable_encoder(error.errors()),
        ).model_dump(by_alias=True),
        status_code=status_code,
    )


if __name__ == "__main__":
    uvicorn.run("app.api_handler:app", host="localhost", port=8080, reload=True)
