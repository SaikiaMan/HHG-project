import os
from pathlib import Path

import serpapi
from dotenv import load_dotenv


# Load variables from .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

if not SERPAPI_KEY:
    raise RuntimeError(
        "SERPAPI_KEY not found. "
        "Add it to the .env file in the project root."
    )


client = serpapi.Client(api_key=SERPAPI_KEY)


def search_image(image_path):
    """
    Upload a local image to SerpApi and perform
    a Google Lens visual search.

    Returns:
        A list of candidate search results.
    """

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    print("Uploading image to visual search...")

    upload = client.upload_image(str(image_path))

    if "error" in upload:
        raise RuntimeError(
            f"Image upload failed: {upload['error']}"
        )

    image_id = upload["image_id"]

    print("Image uploaded successfully.")
    print("Running Google Lens search...")

    results = client.search({
        "engine": "google_lens",
        "image_id": image_id,
        "type": "all",
        "hl": "en",
    })

    if "error" in results:
        raise RuntimeError(
            f"Google Lens search failed: {results['error']}"
        )

    return results


def extract_candidates(results):
    """
    Extract useful candidate pages/images from
    Google Lens results.
    """

    candidates = []

    # Exact matches
    for result in results.get("exact_matches", []):
        candidates.append({
            "title": result.get("title"),
            "url": result.get("link"),
            "source": result.get("source"),
            "image_url": result.get("thumbnail"),
            "match_type": "exact"
        })

    # Visual matches
    for result in results.get("visual_matches", []):
        candidates.append({
            "title": result.get("title"),
            "url": result.get("link"),
            "source": result.get("source"),
            "image_url": result.get("image"),
            "match_type": "visual"
        })

    return candidates


if __name__ == "__main__":

    image_path = PROJECT_ROOT / "python" / "test.jpg"

    results = search_image(image_path)

    candidates = extract_candidates(results)

    print("\n========== SEARCH RESULTS ==========")
    print(f"Candidates found: {len(candidates)}")

    for i, candidate in enumerate(candidates, start=1):

        print(f"\n--- Candidate {i} ---")
        print(f"Title: {candidate['title']}")
        print(f"Source: {candidate['source']}")
        print(f"Type: {candidate['match_type']}")
        print(f"URL: {candidate['url']}")
        print(f"Image: {candidate['image_url']}")