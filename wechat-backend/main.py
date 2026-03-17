from __future__ import annotations

import io
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from typing import Any, Generator
from urllib.parse import quote

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
from PIL import Image
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name
from sqlalchemy.orm import Session

from db import engine, get_db
from models import Base, Issue

APP_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = APP_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR = APP_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

STORES: list[str] = [
    "1001 - 明都店",
    "1010 - 魏村店",
    "1020 - 横林1店",
    "1021 - 百丈店",
    "1022 - 东安1店",
    "1028 - 魏村大顺发",
    "1035 - 雪堰2店",
    "1043 - 南都店",
    "1048 - 郑陆2店",
    "1050 - 湟里店",
    "1052 - 横林大顺发",
    "1056 - 潘家店",
    "1057 - 漕桥店",
    "1063 - 安家3店",
    "1068 - 邹区店",
    "1069 - 镇江店",
    "1077 - 礼河店",
    "1003 - 奔牛1店",
    "1005 - 奔牛2店",
    "1009 - 卜弋店",
    "1015 - 郑陆1店",
    "1016 - 村前店",
    "1042 - 农发区店",
    "1051 - 中天店",
    "1055 - 紫云店",
    "1058 - 学府店",
    "1059 - 怀德店",
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


def _compress_image(
    input_bytes: bytes,
    watermark_type: str = None,
    store_name: str = None,
    issue_id: int = None,
    timestamp: str = None,
) -> bytes:
    """
    Optimized image compression using a two-step approach:
    1. Downscale: If over 1MB, resize so longest side is 2000px
    2. Smart Compression: Save as JPEG quality 80 with optimize.
       If still over 1MB, do ONE more save at quality 60 (floor).
    
    If watermark parameters are provided, applies watermark AFTER resize but BEFORE compression.
    
    Uses io.BytesIO for all intermediate steps to keep operations in-memory.
    
    Returns compressed image bytes (JPEG format).
    """
    SIZE_THRESHOLD = 1024 * 1024  # 1MB
    
    # Step 0: Check initial size - if already under threshold, return original as JPEG
    if len(input_bytes) <= SIZE_THRESHOLD:
        # Convert to JPEG anyway for consistency
        img = Image.open(io.BytesIO(input_bytes))
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        
        # Apply watermark if parameters provided (for small files)
        if watermark_type and store_name and issue_id is not None and timestamp:
            img = _add_watermark(img, watermark_type, store_name, issue_id, timestamp)
        
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        return output.getvalue()
    
    # Step 1: Downscale if over 1MB
    img = Image.open(io.BytesIO(input_bytes))
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    
    width, height = img.size
    LONG_SIDE = 2000
    
    if width > LONG_SIDE or height > LONG_SIDE:
        if width > height:
            new_width = LONG_SIDE
            new_height = int(LONG_SIDE * height / width)
        else:
            new_height = LONG_SIDE
            new_width = int(LONG_SIDE * width / height)
        
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Apply watermark AFTER resize but BEFORE compression (if parameters provided)
    if watermark_type and store_name and issue_id is not None and timestamp:
        img = _add_watermark(img, watermark_type, store_name, issue_id, timestamp)
    
    # Step 2: Save as JPEG with quality=80 and optimize=True
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=80, optimize=True)
    compressed = output.getvalue()
    
    # If still over 1MB, do ONE more save at quality=60 (floor)
    if len(compressed) > SIZE_THRESHOLD:
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=60, optimize=True)
        compressed = output.getvalue()
    
    return compressed


async def _save_upload_with_compression(
    upload_file: UploadFile,
    dest_path: Path,
    watermark_type: str = None,
    store_name: str = None,
    issue_id: int = None,
    timestamp: str = None,
) -> None:
    """
    Read uploaded file, compress if needed, and save to dest_path.
    Handles both 'issue_photo' and 'fix_photo' uploads.
    
    Performance optimization:
    - For images under 1MB: bypass all processing and save original file as-is
    - For images over 1MB: apply two-step compression (downscale + smart compression)
    
    If watermark parameters are provided, applies watermark AFTER resize but BEFORE compression.
    
    If Pillow fails to open a corrupted file, logs error and raises HTTPException(400).
    """
    import logging
    
    logger = logging.getLogger(__name__)
    SIZE_THRESHOLD = 1024 * 1024  # 1MB
    
    try:
        # Read the uploaded file into memory
        input_bytes = upload_file.file.read()
        
        # Check if file is small enough to skip compression - save original as-is
        if len(input_bytes) <= SIZE_THRESHOLD:
            # Even for small files, apply watermark if provided
            if watermark_type and store_name and issue_id is not None and timestamp:
                img = Image.open(io.BytesIO(input_bytes))
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                img = _add_watermark(img, watermark_type, store_name, issue_id, timestamp)
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                input_bytes = output.getvalue()
            
            with dest_path.open("wb") as f:
                f.write(input_bytes)
            return
        
        # File is over 1MB - compress it using two-step approach
        compressed = _compress_image(
            input_bytes,
            watermark_type=watermark_type,
            store_name=store_name,
            issue_id=issue_id,
            timestamp=timestamp,
        )
        
        # Save the compressed result
        with dest_path.open("wb") as f:
            f.write(compressed)
            
    except Exception as e:
        logger.error(f"Image compression failed for {upload_file.filename}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot process image: {upload_file.filename}. The file may be corrupted."
        )
    finally:
        await upload_file.close()


class SafeCleanupFileResponse(FileResponse):
    """
    Custom FileResponse that deletes the file after it has been sent.
    """
    def __init__(self, path: str | os.PathLike[str], **kwargs: Any) -> None:
        super().__init__(path, **kwargs)
        self.file_path = path

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            path = Path(self.file_path)
            if path.exists():
                path.unlink()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


def _safe_filename_part(value: str, *, max_len: int = 30) -> str:
    # Keep Chinese/Unicode for readability, but remove Windows-illegal characters.
    illegal = set('<>:"/\\|?*')
    cleaned = "".join("_" if ch in illegal else ch for ch in (value or "").strip())
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        return "unknown"
    return cleaned[:max_len]


def _unique_upload_filename(kind: str, store: str, original_filename: str | None) -> str:
    ext = ""
    if original_filename:
        ext = Path(original_filename).suffix.lower()
    if not ext:
        ext = ".bin"
    
    # Ensure extension isn't excessively long
    if len(ext) > 10:
        ext = ext[:10]
        
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Limit kind and store to keep total length safe (OS limit is usually 255, we aim for < 100)
    safe_kind = "".join(ch for ch in kind.lower() if ch.isalnum() or ch in ("-", "_"))[:10] or "file"
    safe_store = _safe_filename_part(store, max_len=20)
    uid = uuid4().hex[:8]
    
    filename = f"{safe_kind}_{ts}_{safe_store}_{uid}{ext}"
    return filename


def _get_photo_url(filename: str) -> str:
    """Generate a relative URL for a file in the uploads directory.
    
    Returns a relative path like '/uploads/{filename}' so the browser
    automatically prepends the correct Protocol, Host, and Port.
    This works regardless of the deployment port (e.g., :8000, :3003, etc.)
    """
    return f"/uploads/{filename}"


@app.get("/stores")
def list_stores():
    return {"stores": STORES}


@app.post("/submit-issue")
async def submit_issue(
    request: Request,
    submit_date: str = Form(...),
    store: str = Form(...),
    content: str = Form(...),
    issue_photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if store not in STORES:
        raise HTTPException(status_code=400, detail=f"Invalid store: {store}")

    if not issue_photo.filename:
        raise HTTPException(status_code=400, detail="issue_photo filename is missing")

    # Parse the submitted date string and create datetime
    # Support both "YYYY-MM-DD" and "YYYY-MM-DD HH:mm:ss" formats
    try:
        submitted_dt = datetime.strptime(submit_date, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            submitted_dt = datetime.strptime(submit_date, "%Y-%m-%d")
        except ValueError:
            submitted_dt = datetime.now()

    # Create issue first to get the ID (without photo)
    # We'll save the photo with watermark after getting the ID
    issue = Issue(
        submitted_at=submitted_dt,
        store=store,
        content=content,
        issue_photo="",  # Temporary, will update later
        status="pending",
    )

    try:
        db.add(issue)
        db.commit()
        db.refresh(issue)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error during submission") from e

    # Now save the photo with watermark using the real issue_id
    filename = _unique_upload_filename("issue", store, issue_photo.filename)
    # Ensure .jpg extension for compressed JPEG
    filename = str(Path(filename).with_suffix('.jpg'))
    dest_path = UPLOADS_DIR / filename

    # Format timestamp for watermark
    timestamp = submitted_dt.strftime("%Y-%m-%d %H:%M")

    try:
        await _save_upload_with_compression(
            issue_photo,
            dest_path,
            watermark_type="issue",
            store_name=store,
            issue_id=issue.id,
            timestamp=timestamp,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=500, detail="Failed to save uploaded file") from e

    issue_photo_url = _get_photo_url(filename)
    issue.issue_photo = issue_photo_url

    try:
        db.commit()
        db.refresh(issue)
    except Exception as e:
        db.rollback()
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=500, detail="Database error during update") from e

    return {
        "id": issue.id,
        "submitted_at": issue.submitted_at.strftime("%Y-%m-%d %H:%M") if issue.submitted_at else None,
        "store": issue.store,
        "content": issue.content,
        "issue_photo_url": issue.issue_photo,
        "status": issue.status,
    }


@app.get("/issues/pending")
def get_pending_issues_by_store(store: str, db: Session = Depends(get_db)):
    if store not in STORES:
        raise HTTPException(status_code=400, detail=f"Invalid store: {store}")
    
    # Extract store code prefix (e.g., "1077" from "1077 - 礼河店")
    store_prefix = store.split(" - ")[0] if " - " in store else store
        
    issues = (
        db.query(Issue)
        .filter(Issue.store.like(f"{store_prefix}%"))
        .filter(Issue.fix_photo.is_(None))
        .order_by(Issue.id.desc())
        .all()
    )

    return [
        {
            "id": issue.id,
            "submitted_at": issue.submitted_at.strftime("%Y-%m-%d %H:%M") if issue.submitted_at else None,
            "store": issue.store,
            "content": issue.content,
            "issue_photo_url": issue.issue_photo,
            "status": issue.status,
        }
        for issue in issues
    ]


@app.post("/issues/rectifications")
async def submit_rectifications(
    request: Request,
    ids: list[int] = Form(...),
    fix_photos: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    if len(ids) != len(fix_photos):
        raise HTTPException(
            status_code=400, 
            detail=f"Mismatched data: {len(ids)} IDs and {len(fix_photos)} photos"
        )

    updated_data = []
    now = datetime.now()
    saved_files: list[Path] = []

    try:
        for issue_id, upload in zip(ids, fix_photos):
            if not upload.filename:
                continue

            issue = db.query(Issue).filter(Issue.id == issue_id).first()
            if not issue:
                continue

            filename = _unique_upload_filename("fix", issue.store, upload.filename)
            # Ensure .jpg extension for compressed JPEG
            filename = str(Path(filename).with_suffix('.jpg'))
            dest_path = UPLOADS_DIR / filename

            # Format timestamp for watermark
            fix_timestamp = now.strftime("%Y-%m-%d %H:%M")

            try:
                await _save_upload_with_compression(
                    upload,
                    dest_path,
                    watermark_type="fix",
                    store_name=issue.store,
                    issue_id=issue.id,
                    timestamp=fix_timestamp,
                )
                saved_files.append(dest_path)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to save file for issue {issue_id}") from e

            fix_photo_url = _get_photo_url(filename)
            issue.fix_photo = fix_photo_url
            issue.fix_date = now
            issue.status = "completed"

            updated_data.append({
                "id": issue.id,
                "fix_photo_url": issue.fix_photo,
                "fix_date": issue.fix_date.isoformat(),
                "status": issue.status,
            })

        db.commit()
    except Exception as e:
        db.rollback()
        # Clean up any files saved during this failed transaction
        for p in saved_files:
            if p.exists():
                p.unlink()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Database transaction failed during rectification") from e

    return {"updated": updated_data}


def _add_watermark(
    img: Image.Image,
    watermark_type: str,  # "issue" or "fix"
    store_name: str,
    issue_id: int,
    timestamp: str,
) -> Image.Image:
    """
    Add a text watermark to the image.
    
    Watermark content:
    - Issue Photo: "问题照片 - [门店名称] - [问题编号] - [上传时间]"
    - Rectification Photo: "整改照片 - [门店名称] - [问题编号] - [整改时间]"
    
    Store name should only contain the Chinese part (discard digits and "-").
    Position: Bottom-right corner with a small margin.
    Text: Semi-transparent white with thin black outline.
    """
    # Extract Chinese store name (remove digits and "-")
    # e.g., "1001 - 明都店" -> "明都店"
    chinese_store = store_name
    if " - " in store_name:
        chinese_store = store_name.split(" - ")[-1].strip()
    
    # Build watermark text
    if watermark_type == "issue":
        watermark_text = f"问题照片 - {chinese_store} - #{issue_id} - {timestamp}"
    else:  # fix
        watermark_text = f"整改照片 - {chinese_store} - #{issue_id} - {timestamp}"
    
    # Create a drawing context
    try:
        from PIL import ImageDraw, ImageFont
    except ImportError:
        return img  # Return original if PIL modules not available
    
    draw = ImageDraw.Draw(img)
    
    # Get image dimensions
    width, height = img.size
    
    # Calculate font size (approximately 2% of image height, min 12, max 48)
    font_size = max(12, min(48, int(height * 0.02)))
    
    # Try to load a font that supports Chinese characters
    # Try common Windows fonts that support Chinese
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",   # Microsoft YaHei
        "C:/Windows/Fonts/simhei.ttf", # SimHei
        "C:/Windows/Fonts/simsun.ttc", # SimSun
        "C:/Windows/Fonts/arial.ttf",  # Arial (fallback)
    ]
    
    font = None
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except (OSError, IOError):
            continue
    
    # Use default font if no Chinese font found
    if font is None:
        try:
            font = ImageFont.load_default()
            # Scale up default font if needed
            font_size = max(12, min(48, int(height * 0.02)))
        except Exception:
            font = ImageFont.load_default()
    
    # Get text bounding box
    try:
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except Exception:
        # Fallback estimation if bbox fails
        text_width = len(watermark_text) * font_size * 0.6
        text_height = font_size
    
    # Position: bottom-right corner with margin (5% of image size)
    margin = int(min(width, height) * 0.05)
    x = width - text_width - margin
    y = height - text_height - margin
    
    # Ensure x and y are not negative
    x = max(margin // 2, x)
    y = max(margin // 2, y)
    
    # Draw black outline (stroke)
    outline_width = 2
    for adj_x in range(-outline_width, outline_width + 1):
        for adj_y in range(-outline_width, outline_width + 1):
            if adj_x == 0 and adj_y == 0:
                continue
            draw.text((x + adj_x, y + adj_y), watermark_text, fill="black", font=font)
    
    # Draw white text with transparency
    # PIL doesn't support alpha directly in fill, so we use a workaround
    # by creating an overlay
    try:
        # Try to use RGBA mode for transparency
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create overlay for text
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Draw outline on overlay
        for adj_x in range(-outline_width, outline_width + 1):
            for adj_y in range(-outline_width, outline_width + 1):
                if adj_x == 0 and adj_y == 0:
                    continue
                overlay_draw.text((x + adj_x, y + adj_y), watermark_text, fill=(0, 0, 0, 255), font=font)
        
        # Draw white text on overlay (semi-transparent)
        overlay_draw.text((x, y), watermark_text, fill=(255, 255, 255, 220), font=font)
        
        # Composite overlay onto image
        img = Image.alpha_composite(img, overlay)
        
        # Convert back to RGB for JPEG saving
        img = img.convert('RGB')
    except Exception as e:
        # Fallback: just draw white text with black outline directly
        try:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            draw.text((x, y), watermark_text, fill="white", font=font)
        except Exception:
            pass  # Give up on watermark if it fails
    
    return img


def _resize_image_to_long_side(
    img: Image.Image,
    long_side: int = 250,
    watermark_type: str = None,
    store_name: str = None,
    issue_id: int = None,
    timestamp: str = None,
) -> tuple[bytes, int, int]:
    """
    Resize image so that the LONGER side is exactly 'long_side' pixels.
    Returns the resized image as PNG bytes and its dimensions (width, height).
    
    If watermark parameters are provided, applies watermark after resize but before save.
    """
    width, height = img.size
    
    if width > height:
        # Width is longer - scale width to 250, calculate proportional height
        new_width = long_side
        new_height = int(long_side * height / width)
    else:
        # Height is longer (or equal) - scale height to 250, calculate proportional width
        new_height = long_side
        new_width = int(long_side * width / height)
    
    # Resize with high-quality LANCZOS
    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Apply watermark if parameters provided
    if watermark_type and store_name and issue_id is not None and timestamp:
        resized = _add_watermark(resized, watermark_type, store_name, issue_id, timestamp)
    
    # Save to BytesIO as PNG
    buf = io.BytesIO()
    resized.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue(), new_width, new_height


def _load_and_resize_image(photo_url: str) -> tuple[bytes, int, int] | None:
    """
    Load an image from local uploads folder and resize it.
    Returns PNG bytes and dimensions, or None if not found.
    """
    if not photo_url:
        print(f"DEBUG: photo_url is empty")
        return None
    
    # Extract filename from URL
    filename = photo_url.split('/')[-1]
    if not filename:
        print(f"DEBUG: could not extract filename from {photo_url}")
        return None
    
    local_path = UPLOADS_DIR / filename
    if not local_path.exists():
        print(f"DEBUG: file does not exist: {local_path}")
        return None
    
    try:
        img = Image.open(local_path)
        # Convert to RGB if necessary (handles RGBA, palette, etc.)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        result = _resize_image_to_long_side(img, 250)
        print(f"DEBUG: successfully processed image {filename}, size: {result[1]}x{result[2]}")
        return result
    except Exception as e:
        print(f"Error processing image {filename}: {e}")
        return None


def _cleanup_old_exports():
    """Delete ALL files older than 10 minutes from exports directory."""
    try:
        now = datetime.now()
        for f in EXPORTS_DIR.iterdir():
            try:
                file_time = datetime.fromtimestamp(f.stat().st_mtime)
                if now - file_time > timedelta(minutes=10):
                    f.unlink()
                    print(f"DEBUG: Cleaned up old export file: {f.name}")
            except Exception as e:
                print(f"ERROR cleaning up {f.name}: {e}")
    except Exception as e:
        print(f"ERROR during export cleanup: {e}")


def _file_sender(file_paths: list[Path], chunk_size: int = 8192) -> Generator[bytes, None, None]:
    """Generator that yields file content and deletes all tracked files after sending."""
    main_file = file_paths[0] if file_paths else None
    
    try:
        if main_file and main_file.exists():
            with open(main_file, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
    finally:
        # Delete ALL tracked files after sending
        for file_path in file_paths:
            try:
                if file_path.exists():
                    file_path.unlink()
                    print(f"DEBUG: Deleted file after send: {file_path.name}")
            except Exception as e:
                print(f"ERROR deleting file {file_path.name}: {e}")


@app.get("/export-issues")
def export_issues(
    store: str = "All",
    status: str = "all",
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
):
    # Housekeeping: Clean up old exports (>10 minutes)
    _cleanup_old_exports()
    
    if store != "All" and store not in STORES:
        raise HTTPException(status_code=400, detail=f"Invalid store: {store}")

    q = db.query(Issue)

    if store != "All":
        q = q.filter(Issue.store == store)

    # Filter by start_date
    if start_date and start_date.strip():
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            q = q.filter(Issue.submitted_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

    # Filter by end_date
    if end_date and end_date.strip():
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            q = q.filter(Issue.submitted_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    # Map Chinese status to English
    status_mapping = {
        "待整改": "pending",
        "已整改": "completed",
        "全部": "all",
    }
    
    # Normalize status - support both Chinese and English
    status_input = (status or "全部").strip()
    status_norm = status_mapping.get(status_input, status_input.lower())
    
    if status_norm == "pending":
        q = q.filter(Issue.status == "pending")
    elif status_norm == "completed":
        q = q.filter(Issue.status == "completed")
    elif status_norm == "all":
        pass
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Use '待整改', '已整改', '全部', 'pending', 'completed', or 'all'.",
        )

    issues = q.order_by(Issue.id.asc()).all()

    # Track all temp files for cleanup
    temp_files: list[Path] = []

    # Create xlsxwriter workbook
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_store = _safe_filename_part(store, max_len=20)
    out_name = f"issues_{ts}_{safe_store}.xlsx"
    out_path = EXPORTS_DIR / out_name
    temp_files.append(out_path)

    wb = xlsxwriter.Workbook(str(out_path))
    ws = wb.add_worksheet("Issues")

    # Define column headers - Chinese with new Status column
    headers = ["问题编号", "提交时间", "门店", "问题状态", "问题描述", "问题照片", "整改照片", "整改时间"]
    for col, header in enumerate(headers):
        ws.write(0, col, header)

    # Column indices - using variables for easier maintenance
    COL_ID = 0           # 问题编号
    COL_SUBMITTED_AT = 1 # 提交时间
    COL_STORE = 2        # 门店
    COL_STATUS = 3       # 问题状态
    COL_CONTENT = 4      # 问题描述
    COL_ISSUE_PHOTO = 5 # 问题照片
    COL_FIX_PHOTO = 6    # 整改照片
    COL_FIX_DATE = 7     # 整改时间

    # Column widths (in characters)
    ws.set_column(COL_ID, COL_ID, 10)           # 问题编号
    ws.set_column(COL_SUBMITTED_AT, COL_SUBMITTED_AT, 16)  # 提交时间
    ws.set_column(COL_STORE, COL_STORE, 20)     # 门店
    ws.set_column(COL_STATUS, COL_STATUS, 10)  # 问题状态
    ws.set_column(COL_CONTENT, COL_CONTENT, 45) # 问题描述 (with text_wrap)
    ws.set_column(COL_ISSUE_PHOTO, COL_ISSUE_PHOTO, 38)  # 问题照片
    ws.set_column(COL_FIX_PHOTO, COL_FIX_PHOTO, 38)      # 整改照片
    ws.set_column(COL_FIX_DATE, COL_FIX_DATE, 16)  # 整改时间

    # Header row height
    ws.set_row(0, 25)

    # Define formats
    center_format = wb.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
    })

    # Border format for all cells
    border_format = wb.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
    })

    # Process each issue
    for row_idx, issue in enumerate(issues, 1):
        # Pre-calculate image dimensions for this row
        issue_img_width = 0
        issue_img_height = 0
        issue_img_bytes = None
        fix_img_width = 0
        fix_img_height = 0
        fix_img_bytes = None

        # Load issue photo dimensions
        if issue.issue_photo:
            try:
                img_result = _load_and_resize_image(issue.issue_photo)
                if img_result:
                    issue_img_bytes, issue_img_width, issue_img_height = img_result
            except Exception as e:
                print(f"ERROR loading issue photo for row {row_idx}: {e}")

        # Load fix photo dimensions
        if issue.fix_photo:
            try:
                img_result = _load_and_resize_image(issue.fix_photo)
                if img_result:
                    fix_img_bytes, fix_img_width, fix_img_height = img_result
            except Exception as e:
                print(f"ERROR loading fix photo for row {row_idx}: {e}")

        # Calculate max dimensions for this row
        max_img_height = max(issue_img_height, fix_img_height)
        max_img_width = max(issue_img_width, fix_img_width)

        # Set row height based on max image height (or default if no images)
        if max_img_height > 0:
            row_height_pts = max_img_height * 0.75 + 10
        else:
            row_height_pts = 20  # Default text line height
        ws.set_row(row_idx, row_height_pts)

        # Set column widths for image columns (use fixed 38 for consistency)
        ws.set_column(COL_ISSUE_PHOTO, COL_ISSUE_PHOTO, 38)
        ws.set_column(COL_FIX_PHOTO, COL_FIX_PHOTO, 38)

        # Write all cell values with border format using column variables
        ws.write(row_idx, COL_ID, issue.id, border_format)

        submitted_at_str = issue.submitted_at.strftime("%Y-%m-%d %H:%M") if issue.submitted_at else ""
        ws.write(row_idx, COL_SUBMITTED_AT, submitted_at_str, border_format)

        ws.write(row_idx, COL_STORE, issue.store, border_format)

        status_display = "待整改" if issue.status == "pending" else "已整改"
        ws.write(row_idx, COL_STATUS, status_display, border_format)

        ws.write(row_idx, COL_CONTENT, issue.content, border_format)

        fix_date_str = issue.fix_date.strftime("%Y-%m-%d %H:%M") if issue.fix_date else ""
        ws.write(row_idx, COL_FIX_DATE, fix_date_str, border_format)

        # Column F: 问题照片 (Issue Photo) - column 5
        if issue_img_bytes:
            try:
                # Save image to temp file for xlsxwriter
                temp_img_path = EXPORTS_DIR / f"temp_issue_{row_idx}.png"
                temp_files.append(temp_img_path)
                with open(temp_img_path, "wb") as f:
                    f.write(issue_img_bytes)

                # Calculate y_offset to center image vertically in the row
                if max_img_height > issue_img_height:
                    y_offset = (max_img_height - issue_img_height) / 2
                else:
                    y_offset = 1

                # Write empty cell with border first
                ws.write(row_idx, COL_ISSUE_PHOTO, "", border_format)

                # Insert image with object_position=1 (Move and size with cells)
                ws.insert_image(
                    row_idx, COL_ISSUE_PHOTO,
                    str(temp_img_path),
                    {
                        'x_offset': 1,
                        'y_offset': int(y_offset),
                        'x_scale': 1,
                        'y_scale': 1,
                        'object_position': 1,  # Move and size with cells
                    }
                )

                print(f"DEBUG: Added issue photo to row {row_idx}, col F, size: {issue_img_width}x{issue_img_height}, y_offset: {y_offset}")
            except Exception as e:
                print(f"ERROR adding issue photo for row {row_idx}: {e}")

        # Column G: 整改照片 (Fix Photo) - column 6
        if fix_img_bytes:
            try:
                # Save image to temp file for xlsxwriter
                temp_img_path = EXPORTS_DIR / f"temp_fix_{row_idx}.png"
                temp_files.append(temp_img_path)
                with open(temp_img_path, "wb") as f:
                    f.write(fix_img_bytes)

                # Calculate y_offset to center image vertically in the row
                if max_img_height > fix_img_height:
                    y_offset = (max_img_height - fix_img_height) / 2
                else:
                    y_offset = 1

                # Write empty cell with border first
                ws.write(row_idx, COL_FIX_PHOTO, "", border_format)

                # Insert image with object_position=1 (Move and size with cells)
                ws.insert_image(
                    row_idx, COL_FIX_PHOTO,
                    str(temp_img_path),
                    {
                        'x_offset': 1,
                        'y_offset': int(y_offset),
                        'x_scale': 1,
                        'y_scale': 1,
                        'object_position': 1,  # Move and size with cells
                    }
                )

                print(f"DEBUG: Added fix photo to row {row_idx}, col G, size: {fix_img_width}x{fix_img_height}, y_offset: {y_offset}")
            except Exception as e:
                print(f"ERROR adding fix photo for row {row_idx}: {e}")

    # Close workbook
    wb.close()

    # Return using StreamingResponse with generator that deletes all tracked files after send
    # URL-encode the filename for proper handling of Chinese characters
    encoded_filename = quote(out_name)
    return StreamingResponse(
        _file_sender(temp_files),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={encoded_filename}"}
    )


@app.post("/delete-issues")
async def delete_issues(request: Request, db: Session = Depends(get_db)):
    """
    Delete issues older than before_date with matching status.
    Accepts JSON payload: { "before_date": "YYYY-MM-DD", "status_filter": "completed" | "all" }
    """
    # Debug: Print request info
    content_type = request.headers.get("content-type", "")
    print(f"DEBUG: delete-issues called, content-type: {content_type}")
    
    # Parse JSON body
    try:
        body = await request.json()
        print(f"DEBUG: Received data: {body}")
        before_date = body.get("before_date")
        status_filter = body.get("status_filter")
    except Exception as e:
        print(f"DEBUG: Error parsing JSON: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {str(e)}")

    if not before_date:
        raise HTTPException(status_code=400, detail="Missing before_date")
    
    if status_filter not in ("completed", "all"):
        raise HTTPException(status_code=400, detail="Invalid status_filter. Use 'completed' or 'all'.")

    # Parse the before_date
    try:
        cutoff_dt = datetime.strptime(before_date, "%Y-%m-%d")
        # Set to end of day to include all records from that day
        cutoff_dt = cutoff_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid before_date format. Use YYYY-MM-DD")

    # Build query based on status_filter
    q = db.query(Issue).filter(Issue.submitted_at <= cutoff_dt)
    
    if status_filter == "completed":
        q = q.filter(Issue.status == "completed")
    # "all" means no status filter

    # Get all issues to be deleted
    issues_to_delete = q.all()
    deleted_count = 0

    for issue in issues_to_delete:
        # Delete issue_photo file if exists
        if issue.issue_photo:
            try:
                filename = issue.issue_photo.split('/')[-1]
                if filename:
                    file_path = UPLOADS_DIR / filename
                    if file_path.exists():
                        file_path.unlink()
                        print(f"DEBUG: Deleted issue photo: {file_path}")
                    else:
                        print(f"DEBUG: Issue photo file not found (skipping): {file_path}")
            except Exception as e:
                print(f"ERROR deleting issue photo for issue {issue.id}: {e}")

        # Delete fix_photo file if exists
        if issue.fix_photo:
            try:
                filename = issue.fix_photo.split('/')[-1]
                if filename:
                    file_path = UPLOADS_DIR / filename
                    if file_path.exists():
                        file_path.unlink()
                        print(f"DEBUG: Deleted fix photo: {file_path}")
                    else:
                        print(f"DEBUG: Fix photo file not found (skipping): {file_path}")
            except Exception as e:
                print(f"ERROR deleting fix photo for issue {issue.id}: {e}")

        # Delete database record
        try:
            db.delete(issue)
            deleted_count += 1
        except Exception as e:
            print(f"ERROR deleting issue {issue.id}: {e}")
            # Continue with next issue

    # Commit the deletions
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during deletion: {e}")

    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"成功清理 {deleted_count} 条记录及对应图片"
    }
