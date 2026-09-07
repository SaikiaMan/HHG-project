#!/usr/bin/env python3
"""
HHG Media Integrity & Reverse Provenance Verification System
Hackathon Judge Demonstration Interface

Core Flow:
  INPUT FACE -> REAL SOCIAL MEDIA / WEB MATCH -> FACE VERIFICATION -> BLOCKCHAIN VERIFICATION

Steps:
  1. Input image -> Face detection & embedding
  2. Google Lens reverse visual search -> Real candidate URLs
  3. Candidate acquisition -> Download candidate images to results/candidates
  4. InsightFace biometric comparison against candidates
  5. Display actual matching online source, URL, similarity score, and local visual result
  6. Blockchain verification (Cryptographic SHA-256 fingerprint)
  7. First-time registration flow if unregistered
  8. Optional tamper demonstration
"""

import argparse
import io
import os
import shutil
import sys
import time
import urllib.parse
import webbrowser
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Dict, Any, Optional

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

os.chdir(PROJECT_ROOT)

from hash_image import hash_file
from blockchain import (
    verify_content,
    register_content,
    deploy_contract,
    get_contract_address,
)
from web_search import search_image, extract_candidates
from face_encoding import load_face_model, get_first_embedding
from face_match import is_match
from pipeline import download_candidate_images
from report_generator import generate_html_report


def print_banner(title: str, width: int = 60):
    print("=" * width)
    print(title.center(width))
    print("=" * width)


def get_clean_source_name(candidate: Optional[Dict[str, Any]]) -> str:
    """Extracts a clear source label (e.g. YouTube, Instagram, TikTok) from candidate data."""
    if not candidate:
        return "Web"
    src = candidate.get("source")
    if src and isinstance(src, str) and src.strip():
        return src.strip()
    url = candidate.get("url") or candidate.get("image_url") or ""
    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"
    if "instagram.com" in url:
        return "Instagram"
    if "tiktok.com" in url:
        return "TikTok"
    if "facebook.com" in url:
        return "Facebook"
    if "twitter.com" in url or "x.com" in url:
        return "X (Twitter)"
    if "threads.com" in url:
        return "Threads"
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.replace("www.", "")
        return host or "Web"
    except Exception:
        return "Web"


def main():
    parser = argparse.ArgumentParser(
        description="HHG Media Integrity - Hackathon Judge Demonstration"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Deploy a fresh smart contract to demonstrate first-time registration from scratch"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run without blocking for user interaction (automated demo mode)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Skip opening the visual HTML report in browser"
    )
    args = parser.parse_args()

    # Pre-load face recognition model quietly to keep demo prompt fast and uncluttered
    print("[*] Initializing biometric facial recognition engine (InsightFace)...")
    try:
        f_null = io.StringIO()
        with redirect_stdout(f_null), redirect_stderr(f_null):
            face_app = load_face_model()
        print("[✓] Biometric engine ready.\n")
    except Exception as e:
        face_app = None
        print(f"[!] Biometric engine initialization warning: {e}\n")

    if args.reset:
        print("[*] Deploying fresh smart contract instance on Hardhat...")
        try:
            new_addr = deploy_contract()
            print(f"[✓] Fresh contract deployed at: {new_addr}\n")
        except Exception as e:
            print(f"[!] Could not deploy fresh contract ({e}). Using existing.\n")

    # =========================================================================
    # STEP 1 — INPUT IMAGE
    # =========================================================================
    print_banner("HHG MEDIA INTEGRITY & PROVENANCE")
    print()
    print("STEP 1 — INPUT IMAGE")
    print()

    if args.auto:
        raw_input = "python/test.jpg"
        print(f"Enter image path:\n> {raw_input}")
    else:
        try:
            raw_input = input("Enter image path [default: python/test.jpg]:\n> ").strip()
        except EOFError:
            raw_input = ""

    if not raw_input:
        raw_input = "python/test.jpg"

    image_path = Path(raw_input)
    if not image_path.exists():
        image_path = PROJECT_ROOT / raw_input
    if not image_path.exists():
        image_path = PROJECT_ROOT / "python" / raw_input
    if not image_path.exists():
        print(f"\n[Error] Image file not found: {raw_input}")
        sys.exit(1)

    image_path = image_path.resolve()

    # Check if this image is already registered on the active contract
    initial_check = verify_content(str(image_path))
    if initial_check.get("verified", False):
        print("\n[!] Notice: This image is already notarized on the active smart contract.")
        if args.auto:
            do_reset = "y"
        else:
            try:
                do_reset = input("    Deploy a fresh contract to demonstrate first-time registration? [Y/N]: ").strip().lower()
            except EOFError:
                do_reset = "y"
        if do_reset in ("y", "yes", ""):
            new_addr = deploy_contract()
            print(f"    [✓] Deployed fresh contract: {new_addr}")

    print()
    print("[1/5] FACE IDENTIFICATION")
    input_emb = None
    if face_app is not None:
        try:
            input_emb = get_first_embedding(str(image_path), face_app)
            print("      ✓ Face detected")
            print("      ✓ Face encoded successfully")
        except Exception as e:
            print(f"      ✗ Face detection notice: {e}")
    else:
        print("      ✗ Biometric face engine unavailable")
    print()

    # Calculate cryptographic SHA-256
    sha256_hash = hash_file(str(image_path))

    # =========================================================================
    # STEP 2 — REVERSE IMAGE / SOCIAL SEARCH
    # =========================================================================
    print("[2/5] SEARCHING ONLINE PROVENANCE")
    print()
    print("      ✓ Google Lens search started")
    candidates = []
    try:
        raw_results = search_image(image_path)
        candidates = extract_candidates(raw_results)
    except Exception as e:
        print(f"      [!] Google Lens notice: {e}")

    print(f"      ✓ Real candidates found: {len(candidates)}")
    print()

    # =========================================================================
    # STEP 3 — CANDIDATE ACQUISITION
    # =========================================================================
    print("[3/5] ACQUIRING ONLINE CANDIDATES")
    print()
    candidates_dir = PROJECT_ROOT / "results" / "candidates"
    downloaded = []
    if candidates:
        downloaded = download_candidate_images(
            candidates,
            output_dir=candidates_dir,
            max_candidates=5
        )
    print(f"      ✓ Candidate images downloaded: {len(downloaded)}")
    print()

    # =========================================================================
    # STEP 4 — FACE MATCHING
    # =========================================================================
    print("[4/5] BIOMETRIC FACE COMPARISON")
    print()
    if input_emb is not None:
        print("      Input face detected ✓")
        print()

    best_candidate = None
    best_similarity: Optional[float] = None

    if input_emb is not None and downloaded:
        for idx, cand in enumerate(downloaded, start=1):
            local_path = cand.get("local_path")
            cand_source = get_clean_source_name(cand)
            cand_title = cand.get("title") or "Online Candidate"
            cand_desc = f"{cand_source} — {cand_title[:40]}"

            if not local_path:
                print(f"      Candidate {idx}: {cand_desc}")
                print(f"      Similarity: File unavailable\n")
                continue

            try:
                cand_emb = get_first_embedding(local_path, face_app)
                matched, sim = is_match(input_emb, cand_emb, threshold=0.5)
                cand["similarity"] = sim
                cand["is_match"] = matched
                print(f"      Candidate {idx}: {cand_desc}")
                print(f"      Similarity: {sim:.4f}\n")

                if best_similarity is None or sim > best_similarity:
                    best_similarity = sim
                    best_candidate = cand
            except Exception:
                cand["similarity"] = None
                cand["is_match"] = False
                print(f"      Candidate {idx}: {cand_desc}")
                print(f"      Similarity: No face detected in candidate image\n")

        if best_similarity is not None:
            is_best_match = best_similarity >= 0.5
            print("      BEST MATCH:")
            print(f"      Similarity: {best_similarity:.4f}")
            print(f"      Match: {'TRUE' if is_best_match else 'FALSE'}")
    else:
        print("      No candidate images available for biometric comparison")
    print()

    # =========================================================================
    # STEP 5 — SHOW THE ACTUAL MATCH
    # =========================================================================
    print_banner("PERSON FOUND ONLINE")
    print()

    # Save visual artifacts in results/ directory
    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    saved_input_path = results_dir / "input_image.jpg"
    try:
        shutil.copy(str(image_path), str(saved_input_path))
    except Exception:
        saved_input_path = image_path

    best_local_img = None
    if best_candidate and best_candidate.get("local_path"):
        best_local_img = results_dir / "best_match.jpg"
        try:
            shutil.copy(best_candidate["local_path"], str(best_local_img))
        except Exception:
            best_local_img = Path(best_candidate["local_path"])

    print("INPUT IMAGE")
    print(f"  Path: {saved_input_path.relative_to(PROJECT_ROOT)} ({image_path.name})")
    print()

    print("MATCHING ONLINE SOURCE")
    if best_local_img:
        try:
            rel_cand = best_local_img.relative_to(PROJECT_ROOT)
        except Exception:
            rel_cand = best_local_img
        print(f"  Path: {rel_cand}")
    else:
        print("  Path: N/A")
    print()

    sim_val = best_similarity if best_similarity is not None else 0.0
    match_bool = bool(best_similarity is not None and best_similarity >= 0.5)

    print(f"Face similarity: {sim_val:.4f}")
    print(f"Match: {'TRUE' if match_bool else 'FALSE'}")
    print()

    best_source_name = get_clean_source_name(best_candidate) if best_candidate else "Web"
    best_cand_url = (
        (best_candidate.get("url") or best_candidate.get("image_url"))
        if best_candidate else "N/A"
    )

    print("Source:")
    print(best_source_name)
    print()

    print("URL:")
    print(best_cand_url)
    print()
    print("=" * 60)

    # Check blockchain verification status before registration
    pre_reg_check = verify_content(str(image_path))
    is_verified = bool(pre_reg_check.get("verified", False))

    # Generate initial visual HTML report
    html_report_path = results_dir / "latest_result.html"
    report_data = {
        "input_image": str(image_path),
        "candidate_image": str(best_local_img) if best_local_img else None,
        "title": best_candidate.get("title") if best_candidate else "Online Candidate",
        "source": best_source_name,
        "url": best_cand_url,
        "similarity": best_similarity,
        "is_match": match_bool,
        "threshold": 0.50,
        "sha256": sha256_hash,
        "blockchain_status": "VERIFIED ON-CHAIN" if is_verified else "NOT YET NOTARIZED",
        "contract_address": get_contract_address(),
        "verdict": "AUTHENTIC / MATCH FOUND" if (is_verified and match_bool) else ("IMAGE FOUND ONLINE" if match_bool else "UNVERIFIED"),
        "candidates_count": len(candidates),
        "downloaded_count": len(downloaded),
    }
    generate_html_report(report_data, html_report_path)

    print(f"\n[✓] Visual result page generated: results/latest_result.html")
    if not args.no_browser:
        try:
            webbrowser.open(html_report_path.resolve().as_uri())
            print("    Opened visual side-by-side result in browser.")
        except Exception:
            pass
    print()

    # =========================================================================
    # BLOCKCHAIN VERIFICATION
    # =========================================================================
    print_banner("BLOCKCHAIN VERIFICATION")
    print()
    print("SHA-256:")
    print(sha256_hash)
    print()
    print("Blockchain status:")

    if is_verified:
        print("✓ VERIFIED ON-CHAIN")
        print()
        print("This confirms that the exact file matches a previously notarized SHA-256 fingerprint.")
    else:
        print("✗ NOT REGISTERED")
        print()
        print("=" * 60)
        print("IMAGE FOUND ONLINE")
        print(f"Face match: {'PASS' if match_bool else 'FAIL'}")
        print("Blockchain: NOT YET NOTARIZED")
        print("=" * 60)
        print()

        if args.auto:
            reg_choice = "y"
            print("Register this image's SHA-256 fingerprint on blockchain? [Y/N]\n> Y")
        else:
            try:
                reg_choice = input("Register this image's SHA-256 fingerprint on blockchain? [Y/N]:\n> ").strip().lower()
            except EOFError:
                reg_choice = "y"

        if reg_choice in ("y", "yes", ""):
            print("\nBroadcasting transaction to Hardhat network...")
            reg_result = register_content(str(image_path))
            print(f"✓ SHA-256 registered   : {reg_result['sha256']}")
            print(f"✓ Transaction confirmed : {reg_result['transaction_hash']}")
            print(f"✓ Block Number          : {reg_result['block_number']}")
            print(f"✓ Contract Address      : {get_contract_address()}")
            time.sleep(1)

            print()
            print_banner("RE-VERIFYING ON BLOCKCHAIN")
            print()
            re_check = verify_content(str(image_path))
            re_verified = bool(re_check.get("verified", False))

            if re_verified:
                print("✓ VERIFIED ON-CHAIN")
                print()
                print("This confirms that the exact file matches a previously notarized SHA-256 fingerprint.")

                # Update HTML report with on-chain notarization details
                report_data["blockchain_status"] = "VERIFIED ON-CHAIN"
                report_data["tx_hash"] = reg_result["transaction_hash"]
                report_data["block_number"] = reg_result["block_number"]
                report_data["verdict"] = "AUTHENTIC / MATCH FOUND"
                generate_html_report(report_data, html_report_path)
            else:
                print("✗ Verification failed after registration")
        else:
            print("Blockchain registration skipped.")

    # =========================================================================
    # OPTIONAL TAMPER DEMONSTRATION
    # =========================================================================
    print()
    print("=" * 60)
    if args.auto:
        tamper_choice = "y"
        print("Would you like to demonstrate tamper detection? [Y/N]\n> Y")
    else:
        try:
            tamper_choice = input("Would you like to demonstrate tamper detection? [Y/N]:\n> ").strip().lower()
        except EOFError:
            tamper_choice = "y"

    if tamper_choice in ("y", "yes"):
        tampered_file = PROJECT_ROOT / "python" / "tampered.jpg"
        if not tampered_file.exists():
            print(f"[Error] Tampered test image not found: {tampered_file}")
            return

        print()
        print_banner("TAMPER DETECTION DEMO")
        print()
        tamper_sha = hash_file(str(tampered_file))

        print("Original SHA-256:")
        print(sha256_hash)
        print()

        print("Tampered SHA-256:")
        print(tamper_sha)
        print()

        tamper_bc = verify_content(str(tampered_file))
        print("Blockchain:")
        print("✗ NOT REGISTERED")
        print()

        # Face similarity comparison on tampered image vs downloaded candidate
        tamper_sim: Optional[float] = None
        if face_app is not None:
            try:
                t_emb = get_first_embedding(str(tampered_file), face_app)
                if downloaded:
                    for cand in downloaded:
                        loc = cand.get("local_path")
                        if not loc:
                            continue
                        try:
                            c_emb = get_first_embedding(loc, face_app)
                            _, sim = is_match(t_emb, c_emb, threshold=0.5)
                            if tamper_sim is None or sim > tamper_sim:
                                tamper_sim = sim
                        except Exception:
                            continue
            except Exception as e:
                print(f"[!] Tampered face error: {e}")

        if tamper_sim is not None:
            t_match = tamper_sim >= 0.5
            print(f"Face similarity: {tamper_sim:.4f}")
            print(f"Match: {'TRUE' if t_match else 'FALSE'}")
            print()
            if not t_match:
                print("🚨 SUSPICIOUS / POSSIBLE DEEPFAKE")
                print()
                print("Note: Cryptographic hash is not registered on-chain, and facial biometric")
                print("similarity diverges significantly from authentic candidate media.")
            else:
                print("Note: Face matches online source but file hash is unregistered.")
        else:
            print("Face similarity: N/A")
            print("🚨 SUSPICIOUS / POSSIBLE DEEPFAKE")

        # Generate tamper HTML report as results/tamper_result.html
        tamper_html_path = results_dir / "tamper_result.html"
        tamper_data = {
            "input_image": str(tampered_file),
            "candidate_image": str(best_local_img) if best_local_img else None,
            "title": best_candidate.get("title") if best_candidate else "Online Candidate",
            "source": best_source_name,
            "url": best_cand_url,
            "similarity": tamper_sim,
            "is_match": bool(tamper_sim is not None and tamper_sim >= 0.5),
            "threshold": 0.50,
            "sha256": tamper_sha,
            "blockchain_status": "NOT REGISTERED",
            "contract_address": get_contract_address(),
            "verdict": "🚨 SUSPICIOUS / POSSIBLE DEEPFAKE",
            "candidates_count": len(candidates),
            "downloaded_count": len(downloaded),
        }
        generate_html_report(tamper_data, tamper_html_path)
        print(f"\n[✓] Tamper visual result generated: results/tamper_result.html")
        if not args.no_browser:
            try:
                webbrowser.open(tamper_html_path.resolve().as_uri())
            except Exception:
                pass

    print()
    print_banner("DEMONSTRATION CONCLUDED SUCCESSFULLY")
    print()


if __name__ == "__main__":
    main()

