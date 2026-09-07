import io
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Union

import requests
from PIL import Image
from dotenv import load_dotenv
from serpapi import GoogleSearch

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load variables from .env in project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


def prepare_image_payload(image_path: Path, max_bytes: int = 480 * 1024):
    """
    Ensures the image file is within SerpApi's upload size limit (500 KB).
    Compresses/resizes JPEG/PNG images if they exceed the limit.
    """
    with open(image_path, "rb") as f:
        data = f.read()

    ext = image_path.suffix.lower()
    mime_type = "image/png" if ext == ".png" else "image/webp" if ext == ".webp" else "image/jpeg"

    if len(data) <= max_bytes:
        return data, mime_type

    # If larger than limit, resize/compress using Pillow
    img = Image.open(io.BytesIO(data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    quality = 85
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)

    while buffer.tell() > max_bytes and quality > 25:
        buffer = io.BytesIO()
        quality -= 15
        new_w = max(100, int(img.width * 0.8))
        new_h = max(100, int(img.height * 0.8))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        img.save(buffer, format="JPEG", quality=quality)

    return buffer.getvalue(), "image/jpeg"


def upload_image_to_serpapi(image_path: Union[str, Path], api_key: str) -> str:
    """
    Uploads a local image to SerpApi's Image API endpoint and returns an image_id.
    SerpApi requires images for Google Lens to be either public URLs or uploaded via /image.
    """
    path = Path(image_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Image not found for SerpApi upload: {path}")

    print(f"Uploading image to SerpApi Image API ({path.name})...")
    payload_bytes, mime = prepare_image_payload(path)

    response = requests.post(
        "https://serpapi.com/image",
        files={"image": (path.name, payload_bytes, mime)},
        data={"api_key": api_key},
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"SerpApi image upload failed (status {response.status_code}): {response.text}"
        )

    res_json = response.json()
    image_id = res_json.get("image_id")
    if not image_id:
        raise RuntimeError(
            f"SerpApi image upload did not return an image_id: {res_json}"
        )

    return image_id


def search_image(image_source: Union[str, Path], api_key: str = None) -> Dict[str, Any]:
    """
    Perform a Google Lens visual provenance search using a local image path or a web URL.

    Returns:
        Dictionary of SerpApi search results.
    """
    key = api_key or SERPAPI_KEY
    if not key:
        raise RuntimeError(
            "SERPAPI_KEY not found. "
            "Add it to the .env file in the project root."
        )

    # Check if input is a web URL
    is_web_url = isinstance(image_source, str) and (
        image_source.startswith("http://") or image_source.startswith("https://")
    )

    params: Dict[str, Any] = {
        "engine": "google_lens",
        "hl": "en",
        "api_key": key,
    }

    if is_web_url:
        print(f"Running Google Lens visual search for URL: {image_source}...")
        params["url"] = image_source
    else:
        # Local image file -> upload to SerpApi Image API first
        image_path = Path(image_source).resolve()
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        image_id = upload_image_to_serpapi(image_path, key)
        print("Running Google Lens visual search with uploaded image_id...")
        params["image_id"] = image_id

    search = GoogleSearch(params)
    results = search.get_dict()

    if "error" in results:
        raise RuntimeError(
            f"Google Lens search failed: {results['error']}"
        )

    return results


def extract_candidates(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract useful candidate pages/images from Google Lens results.
    """
    candidates = []

    # Exact matches
    for result in results.get("exact_matches", []):
        candidates.append({
            "title": result.get("title"),
            "url": result.get("link"),
            "source": result.get("source"),
            "image_url": result.get("thumbnail"),
            "thumbnail_url": result.get("thumbnail"),
            "match_type": "exact",
        })

    # Visual matches
    for result in results.get("visual_matches", []):
        candidates.append({
            "title": result.get("title"),
            "url": result.get("link"),
            "source": result.get("source"),
            "image_url": result.get("image") or result.get("thumbnail"),
            "thumbnail_url": result.get("thumbnail"),
            "match_type": "visual",
        })

    return candidates


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else PROJECT_ROOT / "python" / "test.jpg"
    print(f"Target: {target}")

    results = search_image(target)
    candidates = extract_candidates(results)

    print("\n========== SEARCH RESULTS ==========")
    print(f"Candidates found: {len(candidates)}")

    for i, candidate in enumerate(candidates[:10], start=1):
        print(f"\n--- Candidate {i} ---")
        title = candidate.get("title") or "No title"
        print(f"Title: {title}")
        print(f"Source: {candidate.get('source')}")
        print(f"Type: {candidate.get('match_type')}")
        print(f"URL: {candidate.get('url')}")
        print(f"Image: {candidate.get('image_url')}")