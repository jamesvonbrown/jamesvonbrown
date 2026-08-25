"""Fetching, shrinking, and hashing listing photos.

Two things matter here. Photos come off Marketplace at 1500-2000px, and
sending them at that size to a vision model costs several times what a
1024px version costs while telling you nothing extra about a scratch — so
everything is downscaled first. And the same photo showing up across
different listings is a strong signal: either a repost, or someone using
stolen photos, and both are worth knowing before driving anywhere.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from PIL import Image, ImageOps

log = logging.getLogger(__name__)

# Marketplace CDN objects to a bare client; a normal UA avoids 403s.
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

MAX_DOWNLOAD_BYTES = 12 * 1024 * 1024


@dataclass
class PreparedImage:
    """One photo, ready to send to a model."""

    source_url: str
    local_path: str | None = None
    media_type: str = "image/jpeg"
    base64_data: str = ""
    width: int = 0
    height: int = 0
    dhash: str = ""
    sha256: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return bool(self.base64_data) and self.error is None

    def as_content_block(self) -> dict:
        """Anthropic image content block."""
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": self.media_type,
                "data": self.base64_data,
            },
        }


@dataclass
class ImageBundle:
    images: list[PreparedImage] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def usable(self) -> list[PreparedImage]:
        return [i for i in self.images if i.ok]

    def content_blocks(self) -> list[dict]:
        return [i.as_content_block() for i in self.usable]


def compute_dhash(img: Image.Image, size: int = 8) -> str:
    """Difference hash — a fingerprint that survives resizing and recompression.

    Compares each pixel to its right-hand neighbour in a tiny greyscale
    version, so the result tracks the image's structure rather than its exact
    bytes. Two listings sharing a dhash are showing the same photograph, even
    if one has been re-saved at a different size.
    """
    small = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    pixels = list(small.getdata())
    bits = 0
    for row in range(size):
        offset = row * (size + 1)
        for col in range(size):
            bits <<= 1
            if pixels[offset + col] > pixels[offset + col + 1]:
                bits |= 1
    return f"{bits:0{size * size // 4}x}"


def hamming_distance(hash_a: str, hash_b: str) -> int:
    """Bit difference between two dhashes.

    <= 4 means the same photograph, re-saved or resized. Note that dhash keys
    on *structure* and is deliberately blind to colour, so a red and a blue
    example of the same product photographed identically will score close.
    That's the right behaviour for catching a reposted photo and the wrong
    tool for telling two items apart — pair it with `sha256` when the question
    is "is this literally the same file".
    """
    if not hash_a or not hash_b or len(hash_a) != len(hash_b):
        return 999
    return bin(int(hash_a, 16) ^ int(hash_b, 16)).count("1")


def prepare_image_bytes(
    data: bytes,
    source_url: str,
    max_edge: int = 1024,
    cache_dir: Path | None = None,
) -> PreparedImage:
    """Decode, orient, downscale, and base64-encode one image."""
    prepared = PreparedImage(source_url=source_url)
    prepared.sha256 = hashlib.sha256(data).hexdigest()[:32]

    try:
        img = Image.open(io.BytesIO(data))
        # Phone photos carry EXIF rotation; without this, a portrait shot
        # reaches the model on its side and every judgement about the item
        # gets made from a sideways picture.
        img = ImageOps.exif_transpose(img)

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        prepared.dhash = compute_dhash(img)

        img.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        prepared.width, prepared.height = img.size

        buffer = io.BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=82, optimize=True)
        encoded = buffer.getvalue()

        prepared.media_type = "image/jpeg"
        prepared.base64_data = base64.standard_b64encode(encoded).decode("ascii")

        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)
            path = cache_dir / f"{prepared.sha256}.jpg"
            path.write_bytes(encoded)
            prepared.local_path = str(path)

    except Exception as exc:
        prepared.error = f"{type(exc).__name__}: {exc}"
        log.debug("image prep failed for %s: %s", source_url, exc)

    return prepared


async def fetch_image(
    client: httpx.AsyncClient,
    url: str,
    max_edge: int,
    cache_dir: Path | None,
) -> PreparedImage:
    try:
        response = await client.get(url, timeout=20.0, follow_redirects=True)
        response.raise_for_status()
        data = response.content
        if len(data) > MAX_DOWNLOAD_BYTES:
            return PreparedImage(source_url=url, error="image too large")
        return await asyncio.to_thread(
            prepare_image_bytes, data, url, max_edge, cache_dir
        )
    except Exception as exc:
        return PreparedImage(source_url=url, error=f"{type(exc).__name__}: {exc}")


async def fetch_images(
    urls: list[str],
    max_images: int = 4,
    max_edge: int = 1024,
    cache_dir: str | Path | None = None,
) -> ImageBundle:
    """Fetch and prepare up to `max_images` photos, concurrently.

    Near-duplicate shots are dropped: Marketplace listings routinely include
    the same photo twice, and paying to analyse it twice buys nothing.
    """
    bundle = ImageBundle()
    if not urls:
        return bundle

    cache = Path(cache_dir) if cache_dir else None
    # Fetch a few extra so duplicates can be dropped without ending up short.
    targets = urls[: max_images + 3]

    async with httpx.AsyncClient(headers={"User-Agent": _UA}) as client:
        results = await asyncio.gather(
            *(fetch_image(client, u, max_edge, cache) for u in targets)
        )

    kept: list[PreparedImage] = []
    for image in results:
        if not image.ok:
            if image.error:
                bundle.errors.append(f"{image.source_url}: {image.error}")
            continue
        if any(hamming_distance(image.dhash, k.dhash) <= 4 for k in kept):
            continue
        kept.append(image)
        if len(kept) >= max_images:
            break

    bundle.images = kept
    return bundle
