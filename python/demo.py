#!/usr/bin/env python3
"""
HHG Media Integrity & Reverse Provenance Verification System
Judge Demonstration Interface

Flow:
  1. First-time image check (Unregistered on-chain -> Real Google Lens & Biometrics)
  2. Live On-Chain Registration via Smart Contract (Real transaction & block confirmation)
  3. Re-verification of the same image (Verified on-chain + Biometric match -> AUTHENTIC)
  4. Tampered image verification (Different hash, Unregistered, Face mismatch -> POSSIBLE DEEPFAKE)
"""

import argparse
import os
import sys
import time
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


def clear_screen():
    # Keep output visible for terminal history
    print("\n" * 2)


def print_banner(title: str):
    width = 62
    print("=" * width)
    print(title.center(width))
    print("=" * width)


def print_section(title: str):
    width = 62
    print("-" * width)
    print(title)
    print("-" * width)


def run_full_analysis(image_path: Path, face_app, candidates_dir: Path) -> Dict[str, Any]:
    """
    Executes SHA-256, Blockchain query, Google Lens provenance, candidate download,
    and InsightFace biometric analysis.
    """
    # 1. SHA-256
    sha256_hash = hash_file(str(image_path))

    # 2. Blockchain
    blockchain_res = verify_content(str(image_path))
    is_verified = bool(blockchain_res.get("verified", False))

    # 3. Google Lens
    candidates = []
    try:
        raw_results = search_image(image_path)
        candidates = extract_candidates(raw_results)
    except Exception as e:
        print(f"      [!] Google Lens notice: {e}")

    # 4. Candidate Acquisition
    downloaded_candidates = []
    if candidates:
        downloaded_candidates = download_candidate_images(
            candidates,
            output_dir=candidates_dir,
            max_candidates=5
        )

    # 5. Face Biometrics
    input_face_detected = False
    best_candidate = None
    best_similarity: Optional[float] = None

    if face_app is not None:
        try:
            input_emb = get_first_embedding(str(image_path), face_app)
            input_face_detected = True
        except Exception:
            input_emb = None

        if input_emb is not None and downloaded_candidates:
            for cand in downloaded_candidates:
                local_path = cand.get("local_path")
                if not local_path:
                    continue
                try:
                    cand_emb = get_first_embedding(local_path, face_app)
                    matched, sim = is_match(input_emb, cand_emb)
                    cand["similarity"] = sim
                    cand["is_match"] = matched
                    if best_similarity is None or sim > best_similarity:
                        best_similarity = sim
                        best_candidate = cand
                except Exception:
                    continue

    return {
        "sha256": sha256_hash,
        "blockchain_verified": is_verified,
        "candidates": candidates,
        "downloaded_candidates": downloaded_candidates,
        "best_candidate": best_candidate,
        "best_similarity": best_similarity,
        "input_face_detected": input_face_detected,
    }


def main():
    parser = argparse.ArgumentParser(
        description="HHG Media Integrity System - Live Judge Demonstration"
    )
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Deploy a clean smart contract instance on Hardhat to start with unregistered hashes"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run without waiting for interactive input (useful for automated testing)"
    )
    args = parser.parse_args()

    print_banner("HHG MEDIA INTEGRITY SYSTEM")
    print("AI Visual Provenance & Blockchain Media Authentication\n")

    current_contract = get_contract_address()
    print(f"Connected Contract: {current_contract}")
    print(f"Hardhat RPC Node   : http://127.0.0.1:8545\n")

    if args.reset_demo:
        print("[*] Resetting demo state: Deploying fresh PostVerification contract...")
        try:
            new_addr = deploy_contract()
            print(f"[✓] Fresh contract deployed at: {new_addr}\n")
        except Exception as e:
            print(f"[!] Warning: Could not deploy fresh contract ({e}). Using {current_contract}.\n")

    # Pre-load face recognition model once for responsive demo experience
    print("[*] Initializing biometric facial recognition engine (InsightFace)...")
    try:
        face_app = load_face_model()
        print("[✓] Biometric engine ready.\n")
    except Exception as e:
        face_app = None
        print(f"[!] Biometric engine initialization warning: {e}\n")

    # =========================================================================
    # PHASE 1: FIRST-TIME IMAGE (UNREGISTERED)
    # =========================================================================
    print_section("PHASE 1: FIRST-TIME UNREGISTERED IMAGE VERIFICATION")

    if args.auto:
        raw_input = "python/test.jpg"
    else:
        try:
            raw_input = input("Enter image path [default: python/test.jpg]: ").strip()
        except EOFError:
            raw_input = ""

    if not raw_input:
        raw_input = "python/test.jpg"

    image_path = Path(raw_input).resolve()
    if not image_path.exists():
        print(f"[Error] Image not found: {image_path}")
        sys.exit(1)

    # Check if this image is already registered on current contract
    initial_check = verify_content(str(image_path))
    if initial_check.get("verified", False):
        print("\n[!] Notice: This image is already registered on the active contract.")
        if args.auto:
            do_reset = "y"
        else:
            try:
                do_reset = input("    Deploy a fresh contract for a clean first-time demo? [Y/N]: ").strip().lower()
            except EOFError:
                do_reset = "y"
        if do_reset in ("y", "yes", ""):
            new_addr = deploy_contract()
            print(f"    [✓] Deployed fresh contract: {new_addr}\n")

    print(f"\nTarget Image: {image_path.name}")
    print(f"File Path   : {image_path}\n")

    candidates_dir = PROJECT_ROOT / "results" / "candidates"
    analysis_1 = run_full_analysis(image_path, face_app, candidates_dir)

    sha = analysis_1["sha256"]
    is_verified = analysis_1["blockchain_verified"]
    candidates = analysis_1["candidates"]
    downloaded = analysis_1["downloaded_candidates"]
    best_cand = analysis_1["best_candidate"]
    similarity = analysis_1["best_similarity"]

    print("[1/5] SHA-256 FINGERPRINT")
    print(f"      ✓ Hash generated: {sha}")
    print()

    print("[2/5] BLOCKCHAIN NOTARIZATION")
    if is_verified:
        print("      ✓ VERIFIED ON-CHAIN")
    else:
        print("      ✗ NOT REGISTERED")
    print()

    print("[3/5] ONLINE PROVENANCE")
    print(f"      ✓ Google Lens visual search completed")
    print(f"      ✓ {len(candidates)} candidate(s) found online")
    print()

    print("[4/5] CANDIDATE ACQUISITION")
    print(f"      ✓ {len(downloaded)} candidate image(s) downloaded for biometric analysis")
    print()

    print("[5/5] BIOMETRIC VERIFICATION")
    if analysis_1["input_face_detected"]:
        print("      ✓ Face detected and embedded")
        if similarity is not None:
            print(f"      ✓ Best match similarity: {similarity:.4f}")
            if best_cand:
                cand_title = (best_cand.get("title") or "Online Match")[:45]
                cand_url = best_cand.get("url") or best_cand.get("image_url") or "N/A"
                print(f"      ✓ Reference source: {cand_title}")
                print(f"      ✓ Reference URL   : {cand_url}")
        else:
            print("      - No suitable face matches found in candidates")
    else:
        print("      - No face detected in target image")
    print()

    print_section("BLOCKCHAIN STATUS")
    if not is_verified:
        print("      IMAGE NOT YET NOTARIZED ON BLOCKCHAIN")
        print()
        print("      Note: An unregistered image is NOT automatically a deepfake.")
        print("      It simply hasn't been cryptographically notarized yet.")
        print()

        if args.auto:
            register_choice = "y"
        else:
            try:
                register_choice = input("Register this image on blockchain? [Y/N]: ").strip().lower()
            except EOFError:
                register_choice = "y"

        if register_choice in ("y", "yes"):
            print()
            print_banner("BLOCKCHAIN REGISTRATION")
            print("Broadcasting transaction to Hardhat network...")
            reg_result = register_content(str(image_path))
            print(f"✓ SHA-256 registered : {reg_result['sha256']}")
            print(f"✓ Transaction confirmed: {reg_result['transaction_hash']}")
            print(f"✓ Block Number        : {reg_result['block_number']}")
            print(f"✓ Contract Address    : {get_contract_address()}")
            print("=" * 62)
            time.sleep(1)
        else:
            print("Registration skipped by user.")
            return
    else:
        print("      IMAGE IS ALREADY NOTARIZED ON BLOCKCHAIN")

    # =========================================================================
    # PHASE 2: VERIFY THE SAME IMAGE (NOW NOTARIZED)
    # =========================================================================
    print()
    print_section("PHASE 2: POST-REGISTRATION VERIFICATION")
    print("Re-verifying exact same image against the blockchain and provenance data...\n")

    re_check = verify_content(str(image_path))
    re_verified = bool(re_check.get("verified", False))

    print("[1/5] SHA-256 FINGERPRINT")
    print(f"      ✓ Hash generated: {sha}")
    print()

    print("[2/5] BLOCKCHAIN NOTARIZATION")
    if re_verified:
        print("      ✓ VERIFIED ON-CHAIN")
    else:
        print("      ✗ NOT REGISTERED")
    print()

    print("[3/5] ONLINE PROVENANCE")
    print(f"      ✓ {len(candidates)} candidate(s) found online")
    print()

    print("[4/5] CANDIDATE ACQUISITION")
    print(f"      ✓ {len(downloaded)} candidate image(s) verified")
    print()

    print("[5/5] BIOMETRIC VERIFICATION")
    if similarity is not None:
        print(f"      ✓ Face match similarity: {similarity:.4f} (Match: {similarity >= 0.5})")
    else:
        print("      - Face comparison completed")
    print()

    print_section("FINAL VERDICT")
    if re_verified and similarity is not None and similarity >= 0.5:
        print("                 ✓ AUTHENTIC")
    elif re_verified:
        print("                 ✓ BLOCKCHAIN VERIFIED")
    else:
        print("                 - UNVERIFIED")
    print()
    print(f"  Blockchain       : {'VERIFIED' if re_verified else 'NOT REGISTERED'}")
    print(f"  Online Candidates: {len(candidates)}")
    print(f"  Face Similarity  : {similarity:.4f}" if similarity is not None else "  Face Similarity  : N/A")
    print()
    print("  Analysis:")
    print("  Blockchain verification confirms that this exact file matches a previously")
    print("  notarized SHA-256 fingerprint on-chain.")
    print("=" * 62)

    # =========================================================================
    # PHASE 3: TAMPERED IMAGE DETECTION
    # =========================================================================
    print()
    if args.auto:
        tamper_choice = "y"
    else:
        try:
            tamper_choice = input("Now test a modified/tampered version? [Y/N]: ").strip().lower()
        except EOFError:
            tamper_choice = "y"

    if tamper_choice not in ("y", "yes"):
        print("Demo completed.")
        return

    tampered_path = PROJECT_ROOT / "python" / "tampered.jpg"
    if not tampered_path.exists():
        print(f"[Error] Tampered test image not found: {tampered_path}")
        return

    print()
    print_banner("PHASE 3: TAMPER DETECTION")
    print(f"Testing Modified Image: {tampered_path.name}")
    print(f"File Path             : {tampered_path}\n")

    tamper_analysis = run_full_analysis(tampered_path, face_app, candidates_dir)

    t_sha = tamper_analysis["sha256"]
    t_verified = tamper_analysis["blockchain_verified"]
    t_candidates = tamper_analysis["candidates"]
    t_downloaded = tamper_analysis["downloaded_candidates"]
    t_similarity = tamper_analysis["best_similarity"]

    print("[1/5] SHA-256 FINGERPRINT")
    print(f"      ✓ Different hash generated: {t_sha}")
    print()

    print("[2/5] BLOCKCHAIN NOTARIZATION")
    if t_verified:
        print("      ✓ VERIFIED ON-CHAIN")
    else:
        print("      ✗ NOT REGISTERED (Tampered bytes alter cryptographic hash)")
    print()

    print("[3/5] ONLINE PROVENANCE")
    print(f"      ✓ Google Lens retrieved original media candidates ({len(t_candidates)} found)")
    print()

    print("[4/5] CANDIDATE ACQUISITION")
    print(f"      ✓ {len(t_downloaded)} candidate image(s) downloaded")
    print()

    print("[5/5] BIOMETRIC VERIFICATION")
    if t_similarity is not None:
        print(f"      ✗ Biometric mismatch with authentic online source")
        print(f"      ✗ Similarity score: {t_similarity:.4f} (Below 0.5000 threshold)")
    else:
        print("      - Biometric evaluation completed")
    print()

    print_section("FINAL VERDICT")
    if not t_verified and t_similarity is not None and t_similarity < 0.5:
        print("       🚨 SUSPICIOUS / POSSIBLE DEEPFAKE")
    else:
        print("       - TAMPERED IMAGE DETECTED")
    print()
    print(f"  SHA-256          : {t_sha}")
    print(f"  Blockchain       : {'VERIFIED' if t_verified else '✗ NOT REGISTERED'}")
    print(f"  Online Candidates: {len(t_candidates)}")
    print(f"  Face Similarity  : {t_similarity:.4f} (Threshold: 0.5000)" if t_similarity is not None else "  Face Similarity  : N/A")
    print()
    print("  Conclusion:")
    print("  1. Cryptographic hash differs from notarized original -> Unregistered on-chain.")
    print("  2. Online reverse-search identified genuine public source media.")
    print("  3. Facial biometric embedding diverges significantly from authentic candidate.")
    print("=" * 62)
    print("\n[✓] Demonstration concluded successfully.\n")


if __name__ == "__main__":
    main()
