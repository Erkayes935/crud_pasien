import os
import logging
import traceback
from datetime import datetime
from typing import Union
from fastapi import Request, FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app_errors.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Dapatkan path absolut ke frontend/templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "frontend", "templates")

# Verifikasi template directory exists
if not os.path.exists(TEMPLATE_DIR):
    logger.warning(f"Template directory tidak ditemukan: {TEMPLATE_DIR}")
    os.makedirs(TEMPLATE_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Error messages mapping
ERROR_MESSAGES = {
    400: "Permintaan tidak valid.",
    401: "Silakan login untuk melanjutkan.",
    403: "Anda tidak memiliki akses ke halaman ini.",
    404: "Halaman tidak ditemukan.",
    405: "Metode HTTP tidak diizinkan.",
    408: "Permintaan timeout.",
    413: "Ukuran file terlalu besar.",
    415: "Tipe media tidak didukung.",
    422: "Data yang dikirim tidak valid.",
    429: "Terlalu banyak permintaan. Coba lagi nanti.",
    500: "Terjadi kesalahan pada server.",
    502: "Gateway error.",
    503: "Layanan sedang tidak tersedia.",
    504: "Gateway timeout."
}

def get_client_ip(request: Request) -> str:
    """Dapatkan IP address client dengan mempertimbangkan proxy"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def log_error(request: Request, exc: Exception, status_code: int):
    """Log error dengan detail lengkap"""
    error_data = {
        "timestamp": datetime.now().isoformat(),
        "client_ip": get_client_ip(request),
        "method": request.method,
        "url": str(request.url),
        "status_code": status_code,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "user_agent": request.headers.get("user-agent", "unknown")
    }
    
    if status_code >= 500:
        logger.error(f"Server Error: {error_data}")
        if os.getenv("DEBUG", "false").lower() == "true":
            logger.error(f"Traceback: {traceback.format_exc()}")
    elif status_code >= 400:
        logger.warning(f"Client Error: {error_data}")
    
    return error_data

def is_api_request(request: Request) -> bool:
    """Deteksi apakah request dari API endpoint"""
    return (
        request.url.path.startswith("/api/") or
        "application/json" in request.headers.get("accept", "") or
        "application/json" in request.headers.get("content-type", "")
    )

def create_error_response(
    request: Request,
    status_code: int,
    message: str,
    detail: Union[str, dict] = None
) -> Union[HTMLResponse, JSONResponse]:
    """Buat response error sesuai tipe request (HTML/JSON)"""
    
    if is_api_request(request):
        response_data = {
            "status": "error",
            "status_code": status_code,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path)
        }
        
        if detail and os.getenv("DEBUG", "false").lower() == "true":
            response_data["detail"] = detail
            
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    # HTML Response
    try:
        context = {
            "request": request,
            "status_code": status_code,
            "message": message,
            "timestamp": datetime.now().strftime("%d %B %Y, %H:%M:%S")
        }
        
        if detail and os.getenv("DEBUG", "false").lower() == "true":
            context["detail"] = detail
            
        return templates.TemplateResponse(
            "error.html",
            context,
            status_code=status_code
        )
    except Exception as template_error:
        logger.error(f"Error rendering template: {template_error}")
        # Fallback ke HTML sederhana jika template error
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error {status_code}</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>Error {status_code}</h1>
            <p>{message}</p>
            <a href="/">Kembali ke Beranda</a>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=status_code)

def register_error_handlers(app: FastAPI):
    """Register semua error handlers ke aplikasi FastAPI"""
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle semua HTTP exceptions"""
        log_error(request, exc, exc.status_code)
        message = ERROR_MESSAGES.get(exc.status_code, exc.detail)
        
        return create_error_response(
            request=request,
            status_code=exc.status_code,
            message=message,
            detail=exc.detail if hasattr(exc, 'detail') else None
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors dari Pydantic"""
        log_error(request, exc, status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        # Format error validation agar lebih user-friendly
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        
        return create_error_response(
            request=request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Data yang dikirim tidak valid.",
            detail={"validation_errors": errors}
        )
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """Handle 404 Not Found"""
        log_error(request, exc, 404)
        return create_error_response(
            request=request,
            status_code=404,
            message=ERROR_MESSAGES[404]
        )
    
    @app.exception_handler(403)
    async def forbidden_handler(request: Request, exc):
        """Handle 403 Forbidden"""
        log_error(request, exc, 403)
        return create_error_response(
            request=request,
            status_code=403,
            message=ERROR_MESSAGES[403]
        )
    
    @app.exception_handler(401)
    async def unauthorized_handler(request: Request, exc):
        """Handle 401 Unauthorized"""
        log_error(request, exc, 401)
        return create_error_response(
            request=request,
            status_code=401,
            message=ERROR_MESSAGES[401]
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc):
        """Handle 500 Internal Server Error"""
        log_error(request, exc, 500)
        return create_error_response(
            request=request,
            status_code=500,
            message=ERROR_MESSAGES[500],
            detail=str(exc) if os.getenv("DEBUG") else None
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle semua unhandled exceptions"""
        logger.critical(
            f"UNHANDLED EXCEPTION: {type(exc).__name__} - {str(exc)}\n"
            f"Path: {request.url.path}\n"
            f"Method: {request.method}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        
        return create_error_response(
            request=request,
            status_code=500,
            message="Terjadi kesalahan tak terduga.",
            detail=str(exc) if os.getenv("DEBUG") else None
        )
    
    logger.info("Error handlers registered successfully")