"""
HHG Media Integrity & Verification Pipeline
Orchestrates:
  1. Cryptographic SHA-256 hashing (hash_image.py)
  2. Smart contract blockchain notarization check (blockchain.py -> PostVerification.sol)
  3. Reverse image web search via Google Lens (web_search.py / SerpApi)
  4. Candidate image acquisition
  5. Biometric face embedding extraction and matching (face_encoding.py, face_match.py)
  6. Multi-signal verification synthesis and verdict generation
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure python/ directory and project root are in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(1, str(PROJECT_ROOT))

# Ensure venv site-packages is in sys.path if running under system python
venv_site_packages = PROJECT_ROOT / "venv" / "Lib" / "site-packages"
if venv_site_packages.exists() and str(venv_site_packages) not in sys.path:
    sys.path.insert(0, str(venv_site_packages))

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Ensure working directory is project root for relative paths (e.g. artifacts/...)
os.chdir(PROJECT_ROOT)

# 1. Cryptographic hashing
from hash_image import hash_file

# 2. Blockchain verification
try:
    from blockchain import verify_content
    BLOCKCHAIN_AVAILABLE = True
    BLOCKCHAIN_IMPORT_ERROR = None
except Exception as err:
    verify_content = None
    BLOCKCHAIN_AVAILABLE = False
    BLOCKCHAIN_IMPORT_ERROR = str(err)

# 3. Reverse web search
try:
    from web_search import search_image, extract_candidates
    WEB_SEARCH_AVAILABLE = True
    WEB_SEARCH_IMPORT_ERROR = None
except Exception as err:
    search_image = None
    extract_candidates = None
    WEB_SEARCH_AVAILABLE = False
    WEB_SEARCH_IMPORT_ERROR = str(err)

# 4. Face biometrics
try:
    from face_encoding import load_face_model, get_first_embedding
    from face_match import cosine_similarity, is_match
    FACE_AVAILABLE = True
    FACE_IMPORT_ERROR = None
except Exception as err:
    load_face_model = None
    get_first_embedding = None
    cosine_similarity = None
    is_match = None
    FACE_AVAILABLE = False
    FACE_IMPORT_ERROR = str(err)


def download_candidate_images(candidates, output_dir, max_candidates=5, timeout=10):
    """
    Downloads usable candidate images from web search results to a local folder.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    count = 0
    for cand in candidates:
        if count >= max_candidates:
            break

        urls_to_try = []
        if cand.get("image_url"):
            urls_to_try.append(cand["image_url"])
        if cand.get("thumbnail_url") and cand["thumbnail_url"] not in urls_to_try:
            urls_to_try.append(cand["thumbnail_url"])

        dest_filename = f"candidate_{count + 1}.jpg"
        dest_path = output_dir / dest_filename

        for img_url in urls_to_try:
            if not img_url or not isinstance(img_url, str) or not img_url.startswith("http"):
                continue

            try:
                req = urllib.request.Request(img_url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    img_data = response.read()
                    if len(img_data) < 200:
                        continue
                    # Verify valid image bytes (prevent HTML redirects/login walls)
                    is_valid_img = (
                        img_data.startswith(b"\xff\xd8") or
                        img_data.startswith(b"\x89PNG") or
                        img_data.startswith(b"RIFF") or
                        img_data.startswith(b"GIF")
                    )
                    if not is_valid_img:
                        continue
                    with open(dest_path, "wb") as f:
                        f.write(img_data)

                    cand_copy = dict(cand)
                    cand_copy["local_path"] = str(dest_path)
                    downloaded.append(cand_copy)
                    count += 1
                    break
            except Exception:
                continue

    return downloaded


def run_pipeline(image_path: str, candidates_dir: str = "results/candidates") -> dict:
    """
    Runs the complete media verification pipeline on the specified image.
    """
    image_file = Path(image_path).resolve()
    if not image_file.exists():
        raise FileNotFoundError(f"Input image not found: {image_file}")

    print("\n" + "=" * 64)
    print("       HHG MEDIA INTEGRITY & VERIFICATION PIPELINE       ")
    print("=" * 64)
    print(f"Target Image: {image_file.name}")
    print(f"Absolute Path: {image_file}")
    print("-" * 64)

    # -------------------------------------------------------------
    # Step 1: SHA-256 Hash
    # -------------------------------------------------------------
    print("\n[Step 1/5] Calculating cryptographic SHA-256 hash...")
    sha256_hash = hash_file(str(image_file))
    print(f"  SHA-256: {sha256_hash}")

    # -------------------------------------------------------------
    # Step 2: Blockchain Verification
    # -------------------------------------------------------------
    print("\n[Step 2/5] Querying Smart Contract on Blockchain...")
    blockchain_verified = False
    if BLOCKCHAIN_AVAILABLE and verify_content is not None:
        try:
            res = verify_content(str(image_file))
            blockchain_verified = bool(res.get("verified", False))
            if blockchain_verified:
                print("  [+] Result: VERIFIED ON-CHAIN (Cryptographic hash is registered)")
            else:
                print("  [-] Result: NOT FOUND (Hash not yet registered on blockchain)")
        except Exception as e:
            print(f"  [!] Notice: Blockchain query failed ({e}). Marked as unverified.")
            blockchain_verified = False
    else:
        print(f"  [!] Notice: Blockchain module unavailable ({BLOCKCHAIN_IMPORT_ERROR}).")

    # -------------------------------------------------------------
    # Step 3: Web Reverse Search (Google Lens / SerpApi)
    # -------------------------------------------------------------
    print("\n[Step 3/5] Performing Google Lens visual provenance search...")
    candidates = []
    web_search_skipped = False

    if WEB_SEARCH_AVAILABLE and search_image is not None and extract_candidates is not None:
        try:
            raw_results = search_image(image_file)
            candidates = extract_candidates(raw_results)
            print(f"  [+] Search successful: Found {len(candidates)} candidate match(es).")
        except Exception as e:
            print(f"  [!] Web search notice: {e}")
            web_search_skipped = True
    else:
        print(f"  [!] Web search skipped: {WEB_SEARCH_IMPORT_ERROR or 'SerpApi not configured'}")
        web_search_skipped = True

    reverse_search_matches = len(candidates)

    # -------------------------------------------------------------
    # Step 4: Download Candidate Images
    # -------------------------------------------------------------
    downloaded_candidates = []
    if candidates:
        print(f"\n[Step 4/5] Downloading top candidate images to '{candidates_dir}'...")
        downloaded_candidates = download_candidate_images(
            candidates,
            output_dir=PROJECT_ROOT / candidates_dir,
            max_candidates=5
        )
        print(f"  [+] Downloaded {len(downloaded_candidates)} usable candidate image(s).")
    else:
        print("\n[Step 4/5] Candidate acquisition skipped (0 web candidates).")

    # -------------------------------------------------------------
    # Step 5: Face Biometrics & Deepfake / Identity Matching
    # -------------------------------------------------------------
    print("\n[Step 5/5] Extracting biometric face embeddings & comparing...")
    best_candidate = None
    best_similarity = None

    if FACE_AVAILABLE and load_face_model is not None and get_first_embedding is not None and is_match is not None:
        try:
            print("  - Loading InsightFace buffalo_l recognition model...")
            face_app = load_face_model()
        except Exception as e:
            face_app = None
            print(f"  [!] Could not initialize face analysis model: {e}")

        if face_app is not None:
            # Encode input image
            input_embedding = None
            try:
                input_embedding = get_first_embedding(str(image_file), face_app)
                print("  [+] Input face detected and encoded successfully.")
            except Exception as e:
                print(f"  [-] Input face detection: {e}")

            # Match against candidates
            if input_embedding is not None and downloaded_candidates:
                print(f"  - Comparing against {len(downloaded_candidates)} downloaded candidate(s)...")
                for idx, cand in enumerate(downloaded_candidates, start=1):
                    local_path = cand.get("local_path")
                    if not local_path:
                        continue
                    try:
                        cand_embedding = get_first_embedding(local_path, face_app)
                        matched, similarity = is_match(input_embedding, cand_embedding)
                        cand["similarity"] = similarity
                        cand["is_match"] = matched
                        cand_title = (cand.get("title") or "Candidate")[:32]
                        print(f"    [{idx}] {cand_title} -> Similarity: {similarity:.4f} (Match: {matched})")

                        if best_similarity is None or similarity > best_similarity:
                            best_similarity = similarity
                            best_candidate = cand
                    except Exception:
                        cand["similarity"] = None
                        cand["is_match"] = False
            elif input_embedding is not None:
                print("  [-] No candidate images available for face comparison.")
    else:
        print(f"  [!] Face biometric module unavailable: {FACE_IMPORT_ERROR}")

    # Determine top candidate URL & similarity
    if best_candidate is not None:
        top_candidate_url = best_candidate.get("url") or best_candidate.get("image_url")
    elif candidates:
        top_candidate_url = candidates[0].get("url") or candidates[0].get("image_url")
    else:
        top_candidate_url = None

    face_match_similarity = round(float(best_similarity), 4) if best_similarity is not None else None

    # -------------------------------------------------------------
    # Verdict Synthesis
    # -------------------------------------------------------------
    if blockchain_verified:
        verdict = "AUTHENTIC (Cryptographically Verified on Blockchain)"
    elif reverse_search_matches > 0:
        if face_match_similarity is not None:
            if face_match_similarity >= 0.5:
                verdict = f"UNREGISTERED MATCH (Face Matches Online Source - Similarity: {face_match_similarity})"
            else:
                verdict = f"SUSPICIOUS / POSSIBLE DEEPFAKE (Face Mismatch with Online Source - Similarity: {face_match_similarity})"
        else:
            verdict = "UNREGISTERED (Online Matches Found, No Face Match Available)"
    else:
        if web_search_skipped:
            verdict = "UNVERIFIED (Not on Blockchain; Web Search Pending API Key)"
        else:
            verdict = "UNVERIFIED (No Blockchain Record or Web Matches Found)"

    structured_result = {
        "sha256": sha256_hash,
        "blockchain_verified": blockchain_verified,
        "reverse_search_matches": reverse_search_matches,
        "top_candidate_url": top_candidate_url,
        "face_match_similarity": face_match_similarity,
        "verdict": verdict,
    }

    # -------------------------------------------------------------
    # Hackathon Demo Summary Report
    # -------------------------------------------------------------
    print("\n" + "=" * 64)
    print("                     VERIFICATION REPORT                        ")
    print("=" * 64)
    print(f" SHA-256 Hash          : {structured_result['sha256']}")
    print(f" Blockchain Verified   : {'YES (Valid on-chain notarization)' if structured_result['blockchain_verified'] else 'NO (Unregistered hash)'}")
    print(f" Reverse Search Matches: {structured_result['reverse_search_matches']}")
    print(f" Top Candidate URL     : {structured_result['top_candidate_url'] or 'N/A'}")
    print(f" Face Match Similarity : {structured_result['face_match_similarity'] if structured_result['face_match_similarity'] is not None else 'N/A'}")
    print(f" VERDICT               : {structured_result['verdict']}")
    print("=" * 64)

    return structured_result


def main():
    parser = argparse.ArgumentParser(
        description="HHG Media Integrity & Reverse Provenance Verification Pipeline"
    )
    parser.add_argument(
        "image_path",
        help="Path to the image file to verify (e.g. python/test.jpg)"
    )
    parser.add_argument(
        "--candidates-dir",
        default="results/candidates",
        help="Directory where candidate web images will be saved (default: results/candidates)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print pure JSON output only"
    )

    args = parser.parse_args()

    # If --json requested, suppress intermediate prints by redirecting stdout temporarily or running directly
    if args.json:
        # Run and print JSON
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        with redirect_stdout(f):
            result = run_pipeline(args.image_path, args.candidates_dir)
        print(json.dumps(result, indent=2))
    else:
        result = run_pipeline(args.image_path, args.candidates_dir)
        print("\nStructured JSON Result:")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
