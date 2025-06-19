from fastapi import FastAPI, Query, Response, Header, HTTPException, Request, File, UploadFile, Form, Body
from pydantic import BaseModel
import qrcode
import io
from typing import Optional, List
from fastapi.responses import StreamingResponse, JSONResponse
import base64
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from fastapi import status
import zipfile
from PIL import Image
import segno
import logging
import sys
import os
import platform
from pathlib import Path
import datetime
from fastapi.middleware.cors import CORSMiddleware

# Determine data directory from environment or use fallback
data_dir = Path(os.getenv('APP_LOG_DIR', '/tmp/logs'))
try:
    data_dir.mkdir(parents=True, exist_ok=True)
except Exception as e:
    logging.warning(f"Could not create {data_dir}, falling back to /tmp/logs: {e}")
    data_dir = Path('/tmp/logs')
    data_dir.mkdir(parents=True, exist_ok=True)

# Configure logging to both file and stdout
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(data_dir / "app.log", mode='a')
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app with CORS enabled
app = FastAPI(
    title="QR Code Generator API",
    description="API for generating QR codes with various options",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Log important information on startup"""
    logger.info("Starting up QR Code Generator API")
    
    # Log system information
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Data directory: {data_dir}")
    
    # Test write permissions
    try:
        test_file = data_dir / "test.txt"
        test_file.write_text("test")
        test_file.unlink()
        logger.info("Successfully verified write permissions to data directory")
    except Exception as e:
        logger.error(f"Failed to write to data directory: {e}")
        logger.info("Application will continue but some features may be limited")
    
    # Log dependency versions
    try:
        import fastapi
        logger.info(f"FastAPI version: {fastapi.__version__}")
    except Exception as e:
        logger.error(f"Error getting FastAPI version: {e}")
    
    try:
        logger.info(f"Pillow version: {Image.__version__}")
    except Exception as e:
        logger.error(f"Error getting Pillow version: {e}")
    
    try:
        logger.info(f"QRCode version: {qrcode.__version__}")
    except Exception as e:
        logger.error(f"Error getting QRCode version: {e}")
    
    try:
        logger.info(f"Segno version: {segno.__version__}")
    except Exception as e:
        logger.error(f"Error getting Segno version: {e}")

@app.get("/")
async def root():
    """Root endpoint that returns API status"""
    return {
        "status": "online",
        "message": "QR Code Generator API is running",
        "docs_url": "/docs",
        "health_check": "/health",
        "data_dir": str(data_dir)
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with detailed status"""
    try:
        # Test QR code generation
        qr = qrcode.QRCode()
        qr.add_data("test")
        qr.make()
        
        # Test file system
        test_file = data_dir / "test_health.txt"
        try:
            test_file.write_text("test")
            test_file.unlink()
            fs_status = "writable"
        except Exception as e:
            fs_status = f"not writable: {str(e)}"
        
        return {
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "python_version": sys.version,
            "platform": platform.platform(),
            "filesystem": {
                "data_dir": str(data_dir),
                "data_dir_exists": data_dir.exists(),
                "data_dir_writable": os.access(data_dir, os.W_OK),
                "write_test": fs_status
            },
            "dependencies": {
                "fastapi": fastapi.__version__,
                "pillow": Image.__version__,
                "qrcode": qrcode.__version__,
                "segno": segno.__version__
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to log all errors"""
    logger.error(f"Global exception handler caught: {exc}")
    logger.error(f"Request path: {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

SUPPORTED_FORMATS = {"png", "svg", "jpeg"}

class QRRequest(BaseModel):
    data: str
    box_size: Optional[int] = 10
    border: Optional[int] = 4
    fill_color: Optional[str] = "black"
    back_color: Optional[str] = "white"
    version: Optional[int] = 1
    error_correction: Optional[str] = "L"  # L, M, Q, H
    format: Optional[str] = "png"  # png, svg, jpeg
    filename: Optional[str] = None  # Optional filename for download
    base64: Optional[bool] = False  # Return as base64 string in JSON

ERROR_CORRECTION_MAP = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}

EXT_MAP = {"png": ".png", "svg": ".svg", "jpeg": ".jpg"}

class BatchQRRequest(BaseModel):
    items: List[QRRequest]

@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"error": exc.errors()})

@app.get("/generate")
def generate_qr(
    data: str = Query(..., description="The data to encode in the QR code"),
    format: str = Query("png", description="Image format: png, svg, or jpeg"),
    filename: Optional[str] = Query(None, description="Optional filename for download"),
    base64_: bool = Query(False, alias="base64", description="Return as base64 string in JSON")
):
    fmt = format.lower()
    if not data:
        raise HTTPException(status_code=400, detail="'data' parameter must not be empty.")
    if fmt not in SUPPORTED_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{fmt}'. Supported formats: {', '.join(SUPPORTED_FORMATS)}.")
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    if fmt == "svg":
        from qrcode.image.svg import SvgImage
        img = qrcode.make(data, image_factory=SvgImage)
        img.save(buf)
        media_type = "image/svg+xml"
    elif fmt == "jpeg":
        img = img.convert("RGB")
        img.save(buf, format="JPEG")
        media_type = "image/jpeg"
    else:
        img.save(buf, format="PNG")
        media_type = "image/png"
    buf.seek(0)
    content = buf.read()
    if base64_:
        b64str = base64.b64encode(content).decode("utf-8")
        return JSONResponse(content={"base64": b64str, "content_type": media_type})
    headers = {}
    if filename:
        ext = EXT_MAP.get(fmt, ".png")
        download_name = filename if filename.endswith(ext) else filename + ext
        headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return Response(content=content, media_type=media_type, headers=headers)

@app.post("/generate")
def generate_qr_post(req: QRRequest):
    fmt = (req.format or "png").lower()
    if not req.data:
        raise HTTPException(status_code=400, detail="'data' field must not be empty.")
    if fmt not in SUPPORTED_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{fmt}'. Supported formats: {', '.join(SUPPORTED_FORMATS)}.")
    error_correction = ERROR_CORRECTION_MAP.get(req.error_correction.upper(), qrcode.constants.ERROR_CORRECT_L)
    qr = qrcode.QRCode(
        version=req.version,
        error_correction=error_correction,
        box_size=req.box_size,
        border=req.border,
    )
    qr.add_data(req.data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=req.fill_color, back_color=req.back_color)
    buf = io.BytesIO()
    if fmt == "svg":
        from qrcode.image.svg import SvgImage
        img = qrcode.make(req.data, image_factory=SvgImage)
        img.save(buf)
        media_type = "image/svg+xml"
    elif fmt == "jpeg":
        img = img.convert("RGB")
        img.save(buf, format="JPEG")
        media_type = "image/jpeg"
    else:
        img.save(buf, format="PNG")
        media_type = "image/png"
    buf.seek(0)
    content = buf.read()
    if req.base64:
        b64str = base64.b64encode(content).decode("utf-8")
        return JSONResponse(content={"base64": b64str, "content_type": media_type})
    headers = {}
    if req.filename:
        ext = EXT_MAP.get(fmt, ".png")
        download_name = req.filename if req.filename.endswith(ext) else req.filename + ext
        headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return Response(content=content, media_type=media_type, headers=headers)

@app.post("/batch_generate")
def batch_generate(req: BatchQRRequest):
    if not req.items or not isinstance(req.items, list):
        raise HTTPException(status_code=400, detail="'items' must be a non-empty list of QR code requests.")
    in_memory_zip = io.BytesIO()
    with zipfile.ZipFile(in_memory_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, item in enumerate(req.items):
            fmt = (item.format or "png").lower()
            if not item.data:
                continue  # skip empty data
            if fmt not in SUPPORTED_FORMATS:
                continue  # skip unsupported formats
            error_correction = ERROR_CORRECTION_MAP.get((item.error_correction or "L").upper(), qrcode.constants.ERROR_CORRECT_L)
            qr = qrcode.QRCode(
                version=item.version,
                error_correction=error_correction,
                box_size=item.box_size,
                border=item.border,
            )
            qr.add_data(item.data)
            qr.make(fit=True)
            img = qr.make_image(fill_color=item.fill_color, back_color=item.back_color)
            buf = io.BytesIO()
            if fmt == "svg":
                from qrcode.image.svg import SvgImage
                img = qrcode.make(item.data, image_factory=SvgImage)
                img.save(buf)
                ext = ".svg"
            elif fmt == "jpeg":
                img = img.convert("RGB")
                img.save(buf, format="JPEG")
                ext = ".jpg"
            else:
                img.save(buf, format="PNG")
                ext = ".png"
            buf.seek(0)
            # Determine filename
            if item.filename:
                filename = item.filename if item.filename.endswith(ext) else item.filename + ext
            else:
                filename = f"qr_{idx+1}{ext}"
            zf.writestr(filename, buf.read())
    in_memory_zip.seek(0)
    return Response(
        content=in_memory_zip.read(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=qr_codes.zip"}
    )

@app.post("/generate_with_logo")
def generate_qr_with_logo(
    data: str = Form(...),
    box_size: int = Form(10),
    border: int = Form(4),
    fill_color: str = Form("black"),
    back_color: str = Form("white"),
    version: int = Form(1),
    format: str = Form("png"),
    filename: str = Form(None),
    base64_: bool = Form(False),
    logo: UploadFile = File(None)
):
    fmt = (format or "png").lower()
    if not data:
        raise HTTPException(status_code=400, detail="'data' field must not be empty.")
    if fmt not in SUPPORTED_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{fmt}'. Supported formats: {', '.join(SUPPORTED_FORMATS)}.")
    error_correction_val = ERROR_CORRECTION_MAP.get('H', qrcode.constants.ERROR_CORRECT_H)
    qr = qrcode.QRCode(
        version=version,
        error_correction=error_correction_val,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGBA")
    # Overlay logo if provided
    if logo is not None:
        try:
            logo_bytes = logo.file.read()
            logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid logo image file.")
        # Resize logo (smaller for better scan reliability)
        qr_width, qr_height = img.size
        factor = 6  # logo covers 1/6 of QR code
        logo_size = min(qr_width, qr_height) // factor
        logo_img = logo_img.resize((logo_size, logo_size), Image.LANCZOS)
        # Calculate position and paste
        pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
        img.paste(logo_img, pos, mask=logo_img)
    buf = io.BytesIO()
    if fmt == "svg":
        from qrcode.image.svg import SvgImage
        img_svg = qrcode.make(data, image_factory=SvgImage)
        img_svg.save(buf)
        media_type = "image/svg+xml"
    elif fmt == "jpeg":
        img = img.convert("RGB")
        img.save(buf, format="JPEG")
        media_type = "image/jpeg"
    else:
        img.save(buf, format="PNG")
        media_type = "image/png"
    buf.seek(0)
    content = buf.read()
    if base64_:
        b64str = base64.b64encode(content).decode("utf-8")
        return JSONResponse(content={"base64": b64str, "content_type": media_type})
    headers = {}
    if filename:
        ext = EXT_MAP.get(fmt, ".png")
        download_name = filename if filename.endswith(ext) else filename + ext
        headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return Response(content=content, media_type=media_type, headers=headers)

@app.post("/generate_artistic")
def generate_artistic_qr(
    data: str = Form(...),
    dark: str = Form("#000"),
    light: str = Form("#fff"),
    border: int = Form(4),
    scale: int = Form(10),
    error_correction: str = Form("L"),
    format: str = Form("png")
):
    fmt = format.lower()
    if not data:
        raise HTTPException(status_code=400, detail="'data' field must not be empty.")
    if fmt not in ["png", "svg"]:
        raise HTTPException(status_code=400, detail="Only PNG and SVG formats are supported for artistic QR codes.")
    try:
        qr = segno.make(data, error=error_correction.upper())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate QR code: {str(e)}")
    buf = io.BytesIO()
    if fmt == "svg":
        qr.save(buf, kind="svg", scale=scale, border=border, dark=dark, light=light)
        media_type = "image/svg+xml"
    else:
        qr.save(buf, kind="png", scale=scale, border=border, dark=dark, light=light)
        media_type = "image/png"
    buf.seek(0)
    return Response(content=buf.read(), media_type=media_type)

def main():
    pass 