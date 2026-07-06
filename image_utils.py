# -*- coding: utf-8 -*-
"""
Image processing utilities.

- Save clipboard image to original file
- Generate blurred thumbnails for card display
- Copy original images back to clipboard for pasting
"""

import os
import io
import hashlib
import struct
from PIL import Image, ImageFilter


def get_data_dir():
    """Get data storage root at %APPDATA%\\ClipboardManager\\"""
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    data_dir = os.path.join(appdata, 'ClipboardManager')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_images_dir():
    """Get original images directory"""
    path = os.path.join(get_data_dir(), 'images')
    os.makedirs(path, exist_ok=True)
    return path


def get_thumbnails_dir():
    """Get thumbnails directory"""
    path = os.path.join(get_data_dir(), 'thumbnails')
    os.makedirs(path, exist_ok=True)
    return path


def _img_debug(msg: str):
    """Write image debug info to log file."""
    try:
        log_path = os.path.join(get_data_dir(), 'image.log')
        with open(log_path, 'a') as f:
            from datetime import datetime
            f.write(f"[{datetime.now()}] {msg}\n")
    except Exception:
        pass


def _get_clipboard_image() -> Image.Image | None:
    """
    Get image from Windows clipboard.
    Handles screenshots (CF_DIB, CF_DIBV5), browser copy-image (PNG/JPG/GIF
    registered formats), and copied image files (FileContents/FileNameW).
    """
    import win32clipboard

    try:
        win32clipboard.OpenClipboard()
    except Exception as e:
        return None

    try:
        # Build map of format_id -> format_name
        format_names = {}
        fmt = 0
        while True:
            fmt = win32clipboard.EnumClipboardFormats(fmt)
            if fmt == 0:
                break
            try:
                name = win32clipboard.GetClipboardFormatName(fmt)
            except Exception:
                name = ''
            format_names[fmt] = name

        _img_debug(f"Formats: {list(format_names.keys())} names={list(format_names.values())}")

        # ── Strategy 1: Standard DIB formats (screenshots) ──
        for fmt_id in (17, 8):  # CF_DIBV5 first, then CF_DIB
            if fmt_id in format_names:
                try:
                    data = win32clipboard.GetClipboardData(fmt_id)
                    if data and len(data) >= 40:
                        img = _dib_to_image(data, f'CF_DIB{fmt_id}')
                        if img:
                            return img
                except Exception as e:
                    _img_debug(f"CF_DIB{fmt_id} error: {e}")

        # ── Strategy 2: Registered image formats (browser copy-image) ──
        for fmt_id, name in format_names.items():
            if fmt_id in (2, 8, 17):  # Already tried
                continue
            # Look for PNG, GIF, JPG, JPEG, JFIF, image/ formats
            name_lower = name.lower()
            if any(tag in name_lower for tag in ('png', 'gif', 'jpg', 'jpeg', 'jfif', 'image/', 'bitmap')):
                try:
                    data = win32clipboard.GetClipboardData(fmt_id)
                    if data and len(data) > 100:
                        img = Image.open(io.BytesIO(data))
                        img.load()
                        _img_debug(f"Format {name}({fmt_id}): {img.size} {img.mode}")
                        return img
                except Exception as e:
                    _img_debug(f"Format {name}({fmt_id}): {e}")

        # ── Strategy 3: File copy (user copied an image file) ──
        # Check if FileContents has image data
        if 49352 in format_names:  # "FileContents"
            try:
                data = win32clipboard.GetClipboardData(49352)
                if data and len(data) > 100:
                    img = Image.open(io.BytesIO(data))
                    img.load()
                    _img_debug(f"FileContents: {img.size} {img.mode}")
                    return img
            except Exception:
                pass

        # Check FileNameW for image file extensions
        if 49159 in format_names:  # "FileNameW"
            try:
                raw = win32clipboard.GetClipboardData(49159)
                if raw:
                    # Handle both bytes (UTF-16LE) and str returns
                    if isinstance(raw, bytes):
                        fname = raw.decode('utf-16-le').rstrip('\x00')
                    else:
                        fname = str(raw).rstrip('\x00')
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico'):
                        if os.path.exists(fname):
                            img = Image.open(fname)
                            img.load()
                            _img_debug(f"FileNameW: opened {fname} {img.size} {img.mode}")
                            return img
                        else:
                            _img_debug(f"FileNameW: file not found: {fname}")
            except Exception as e:
                _img_debug(f"FileNameW error: {e}")

        # ── Strategy 4: Try ALL formats as raw image data ──
        for fmt_id in format_names:
            if fmt_id in (2, 8, 17, 49352, 49159):  # Already tried
                continue
            try:
                data = win32clipboard.GetClipboardData(fmt_id)
                if data and len(data) > 500:
                    # Check for image magic bytes
                    header = data[:8]
                    is_image = (
                        header[:4] == b'\x89PNG' or      # PNG
                        header[:2] == b'\xff\xd8' or     # JPEG
                        header[:4] == b'GIF8' or         # GIF
                        header[:2] == b'BM' or           # BMP
                        header[:4] == b'RIFF'            # WEBP
                    )
                    if is_image:
                        img = Image.open(io.BytesIO(data))
                        img.load()
                        _img_debug(f"Format {fmt_id}: magic bytes match, {img.size}")
                        return img
            except Exception:
                continue

    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass

    # ── Fallback: PIL's ImageGrab ──
    try:
        from PIL import ImageGrab
        img = ImageGrab.grabclipboard()
        if img is not None:
            if isinstance(img, list):
                img = img[0] if len(img) > 0 else None
            if img and hasattr(img, 'size'):
                _img_debug(f"ImageGrab fallback ok: {img.size}")
                return img
    except Exception:
        pass

    return None


def _dib_to_image(dib_data: bytes, fmt_name: str = 'DIB') -> Image.Image | None:
    """Convert DIB data to PIL Image with correct BMP header."""
    try:
        if len(dib_data) < 40:
            return None

        bi_size = struct.unpack_from('<I', dib_data, 0)[0]
        bi_width = abs(struct.unpack_from('<i', dib_data, 4)[0])
        bi_height = abs(struct.unpack_from('<i', dib_data, 8)[0])
        bi_bit_count = struct.unpack_from('<H', dib_data, 14)[0]
        bi_compression = struct.unpack_from('<I', dib_data, 16)[0]
        bi_clr_used = struct.unpack_from('<I', dib_data, 32)[0]

        _img_debug(f"DIB info: {bi_width}x{bi_height}, {bi_bit_count}bit, "
                   f"compression={bi_compression}, size_field={bi_size}")

        # Calculate pixel data offset in BMP file
        offset = 14 + bi_size

        if bi_compression == 3:  # BI_BITFIELDS
            offset += 12  # 3 DWORD masks
        elif bi_compression == 6:  # BI_ALPHABITFIELDS
            offset += 16  # 4 DWORD masks

        if bi_bit_count <= 8:
            num_colors = bi_clr_used if bi_clr_used > 0 else (1 << bi_bit_count)
            offset += num_colors * 4  # RGBQUAD each

        total_size = len(dib_data) + 14
        bmp_header = struct.pack('<HIHHI', 0x4D42, total_size, 0, 0, offset)
        bmp_data = bmp_header + dib_data

        img = Image.open(io.BytesIO(bmp_data))
        img.load()
        _img_debug(f"DIB decoded: {img.size}, mode={img.mode}")
        return img
    except Exception as e:
        _img_debug(f"DIB decode error: {e}")
        return None


def save_clipboard_image() -> tuple[str, str] | None:
    """
    Grab image from clipboard, save original and blurred thumbnail.

    Returns:
        (image_path, thumb_path) on success, None if no image on clipboard
    """
    try:
        img = _get_clipboard_image()
    except Exception as e:
        _img_debug(f"get_clipboard_image exception: {e}")
        return None

    if img is None:
        return None

    _img_debug(f"Got image: {img.size}, mode={img.mode}")

    # Convert to RGB if needed
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode == 'P':
        img = img.convert('RGBA')
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')

    # Generate unique filename based on content hash
    img_hash = hashlib.md5(img.tobytes()).hexdigest()[:12]
    filename = f"img_{img_hash}.png"

    # Save original
    image_path = os.path.join(get_images_dir(), filename)
    img.save(image_path, 'PNG')
    _img_debug(f"Saved: {image_path} ({os.path.getsize(image_path)} bytes)")

    # Generate blurred thumbnail
    thumb_path = os.path.join(get_thumbnails_dir(), filename)
    create_blurred_thumbnail(img, thumb_path)

    return image_path, thumb_path


def create_blurred_thumbnail(image: Image.Image, save_path: str,
                              thumb_width: int = 200, blur_radius: float = 2.5):
    """Generate a blurred thumbnail for preview display."""
    w_percent = thumb_width / float(image.width)
    thumb_height = int(float(image.height) * w_percent)

    thumb = image.copy()
    thumb.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
    thumb = thumb.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    thumb.save(save_path, 'PNG', optimize=True)


def copy_image_to_clipboard(image_path: str) -> bool:
    """Copy original high-quality image to Windows clipboard."""
    import win32clipboard
    try:
        image = Image.open(image_path)
        buf = io.BytesIO()
        image.save(buf, format='BMP')
        bmp_data = buf.getvalue()
        dib_data = bmp_data[14:]

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib_data)
        win32clipboard.CloseClipboard()
        return True
    except Exception as e:
        _img_debug(f"Copy to clipboard failed: {e}")
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        return False


def copy_text_to_clipboard(text: str) -> bool:
    """Copy text to Windows clipboard."""
    import win32clipboard
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        return True
    except Exception as e:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        return False
