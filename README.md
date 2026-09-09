# HHG — Face ID + Blockchain Verification

Hacker House Goa 2026 — Team Texas Codem

## Overview

HHG is a prototype for identifying where an image of a person appears online and verifying the discovered source using biometric face matching and blockchain-based content fingerprinting.

The system starts with only an input image. It then:

1. Detects and encodes the face.
2. Performs a genuine reverse-image search using Google Lens through SerpApi.
3. Retrieves real online image candidates.
4. Compares the input face with faces found in the retrieved candidates.
5. Identifies the strongest matching online source.
6. Generates a SHA-256 fingerprint of the input image.
7. Stores that fingerprint on a blockchain.
8. Re-verifies the exact image against the blockchain record.
9. Detects modifications when the image is changed.

The project was built for Hacker House Goa 2026 by Team Texas Codem.

---

## How It Works

```text
Input Image
     |
     v
Face Detection
     |
     v
Face Encoding
     |
     v
Google Lens Reverse Image Search
     |
     v
Real Online Candidates
     |
     v
Candidate Image Download
     |
     v
Face Embedding Comparison
     |
     v
Best Matching Online Source
     |
     +----------------------+
     |                      |
     v                      v
SHA-256 Fingerprint    Similarity Score
     |
     v
Blockchain Verification
     |
     v
Authentic / Unregistered / Suspicious
```

---

## Core Components

### 1. Face Identification

The system uses InsightFace to detect a face and generate a numerical face embedding.

The embedding represents facial features in a form that can be compared against faces found in online candidate images.

File:

```text
python/face_encoding.py
```

---

### 2. Genuine Online Search

The system uses Google Lens through SerpApi to perform a real reverse-image search.

The search is performed dynamically from the supplied image.

The matching URL is not hardcoded or preselected.

The search can return sources from platforms such as:

* YouTube
* Instagram
* Facebook
* Threads
* TikTok
* Other indexed websites

File:

```text
python/web_search.py
```

---

### 3. Face Matching

Downloaded candidate images are processed using InsightFace.

The input face embedding is compared with candidate face embeddings using cosine similarity.

The current matching threshold is:

```text
0.50
```

A score above the threshold is considered a face match for the prototype.

File:

```text
python/face_match.py
```

The similarity score should be interpreted as a biometric similarity score, not as a percentage probability that two images are the same person.

---

### 4. Blockchain Verification

The system generates a SHA-256 fingerprint of the exact input file.

The fingerprint is stored in a Solidity smart contract.

The blockchain does not determine whether a person is genuine.

Instead, it proves that the exact file being checked matches a fingerprint that was previously registered on-chain.

Smart contract:

```text
contracts/PostVerification.sol
```

The contract provides:

```solidity
storeHash(bytes32 hash)
```

to register a fingerprint and:

```solidity
verifyHash(bytes32 hash)
```

to check whether that fingerprint has previously been registered.

---

## Blockchain Architecture

The prototype currently uses a local Hardhat blockchain.

Network:

```text
Hardhat Local Network
RPC: http://127.0.0.1:8545
Chain ID: 31337
```

This was chosen for the hackathon prototype so that the entire verification process can be demonstrated locally without requiring real cryptocurrency.

The same contract design can later be deployed to a public Ethereum-compatible testnet or mainnet.

---

# Project Structure

```text
HHG-project/
│
├── contracts/
│   └── PostVerification.sol
│
├── python/
│   ├── blockchain.py
│   ├── demo.py
│   ├── face_encoding.py
│   ├── face_match.py
│   ├── hash_image.py
│   ├── pipeline.py
│   ├── report_generator.py
│   ├── web_search.py
│   └── ...
│
├── scripts/
│   └── deployPostVerification.ts
│
├── test/
│   └── PostVerification.ts
│
├── package.json
├── hardhat.config.ts
├── tsconfig.json
├── package-lock.json
└── README.md
```

---

# Requirements

## Software

* Python 3.10+
* Node.js
* npm
* Git
* Windows, macOS, or Linux

## External API

The reverse-image search requires a SerpApi API key.

Create a `.env` file in the project root:

```env
SERPAPI_KEY=your_serpapi_key
```

Do not commit this file.

---

# Installation

Clone the repository:

```bash
git clone https://github.com/SaikiaMan/HHG-project.git
cd HHG-project
```

---

## Python Environment

Create a virtual environment:

### Windows

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install Python dependencies:

```powershell
pip install -r python/requirements.txt
```

If the requirements file is located elsewhere in your local version, install the dependencies listed by the project accordingly.

---

# Node Dependencies

Install the JavaScript dependencies:

```powershell
npm install
```

---

# Configure SerpApi

Create:

```text
.env
```

Add:

```env
SERPAPI_KEY=your_api_key_here
```

The API key is required for Google Lens reverse-image searches.

Never commit `.env` to GitHub.

---

# Run the Blockchain

Open a terminal in the project root:

```powershell
npx hardhat node
```

Keep this terminal running.

The local blockchain will run at:

```text
http://127.0.0.1:8545
```

Do not start a second Hardhat node if port `8545` is already in use.

---

# Deploy the Smart Contract

In a second terminal:

```powershell
python scripts/deployPostVerification.ts
```

If using the Hardhat deployment script directly, use the project's configured Hardhat command for:

```text
scripts/deployPostVerification.ts
```

The deployment address is then used by the Python blockchain integration.

---

# Run Tests

Run the Hardhat test suite:

```powershell
npx hardhat test
```

The tests verify that:

1. A hash can be stored.
2. A stored hash can be verified.
3. A modified hash is rejected.

---

# Run the Full Demo

The easiest way to demonstrate the project is:

```powershell
python python/demo.py
```

The demo performs the complete pipeline:

```text
1. Face identification
2. Online reverse-image search
3. Candidate acquisition
4. Face comparison
5. Matching online source
6. Blockchain verification
7. Blockchain registration if required
8. Re-verification
9. Optional tamper demonstration
```

---

# Clean Hackathon Demo

To start with a fresh blockchain state:

```powershell
python python/demo.py --reset
```

This deploys a fresh contract and starts the demonstration with the image not yet registered on-chain.

The demo can then register the image and immediately verify it again.

To prevent the browser report from opening automatically:

```powershell
python python/demo.py --reset --no-browser
```

---

# Run the Pipeline Directly

Run the pipeline against an image:

```powershell
python python/pipeline.py python/test.jpg
```

Run it against a modified image:

```powershell
python python/pipeline.py python/tampered.jpg
```

JSON output:

```powershell
python python/pipeline.py python/test.jpg --json
```

---

# Example Verification Flow

Suppose the input image has never been registered.

The system can report:

```text
Blockchain: NOT REGISTERED
```

The system then generates the SHA-256 fingerprint and sends a blockchain transaction.

After registration:

```text
Blockchain: VERIFIED
```

Running the exact same file again produces the same SHA-256 fingerprint and therefore verifies successfully.

If the image is modified, even slightly, its SHA-256 fingerprint changes.

For example:

```text
Original:
774f3ed14d3fc766c6ccdf83295329483d6ce1795d18d2a23d42000acc7badcc

Modified:
bd4dbc9f28b9e4515d42c2b86b240831f91479ed53445ef6cfc3df5951b33200
```

The modified fingerprint is not present on-chain, so verification fails.

---

# Demonstration Result

During development, the system successfully demonstrated the following flow:

```text
Input Image
     |
     v
Face detected and encoded
     |
     v
Google Lens
     |
     v
Real online candidates retrieved
     |
     v
Candidate faces compared
     |
     v
Best matching online source identified
     |
     v
SHA-256 fingerprint generated
     |
     v
Fingerprint registered on blockchain
     |
     v
Same image verified successfully
```

The system has also been tested against a modified version of the image.

The modified file produces a different SHA-256 fingerprint and is not verified against the original blockchain record.

---

# Visual Reports

The pipeline can generate HTML reports containing:

* Input image
* Best candidate image
* Face similarity score
* Matching source URL
* Blockchain verification status
* SHA-256 fingerprint
* Verification result

Generated reports include:

```text
latest_result.html
tamper_result.html
```

These reports are intended for demonstration and judging.

---

# Hackathon Requirement Mapping

## Requirement 1 — Face Identification

Implemented using InsightFace.

The system detects and encodes the face from the supplied image.

## Requirement 2 — Genuine Social/Web Search

Implemented using Google Lens through SerpApi.

The search is performed dynamically from the supplied image.

The system does not hardcode the matching result.

## Requirement 3 — Blockchain Verification

Implemented using Solidity and Hardhat.

The SHA-256 fingerprint of the content is registered on-chain and can later be verified.

## Requirement 4 — No Website Required

The project is operated through the terminal and generates an optional HTML report for visual demonstration.

## Requirement 5 — GitHub Repository

Source code, smart contracts, tests, scripts, and documentation are included in this repository.

---

# Important Distinction

The project combines two different forms of verification.

### Biometric Verification

Answers:

> Does the face in the input image resemble the face in the online candidate?

This is handled using InsightFace embeddings and cosine similarity.

### Blockchain Verification

Answers:

> Is this exact file identical to a file whose fingerprint was previously registered?

This is handled using SHA-256 and the smart contract.

Blockchain does not prove that the person is real or that an online post is truthful.

It provides an immutable record of the fingerprint that was registered.

---

# Limitations

This is a hackathon prototype and has several limitations.

### Reverse Image Search

Results depend on what Google Lens can index and return through SerpApi.

### Face Matching

The similarity threshold is experimentally selected for the prototype and should not be treated as a production identity-verification threshold.

### Blockchain

The current demonstration uses a local Hardhat blockchain.

A production system would use a public blockchain or another independently verifiable ledger.

### Identity

A biometric match does not establish a person's legal identity.

It only indicates similarity between facial embeddings.

### Online Sources

The presence of an image online does not prove that the source is authentic or that the account belongs to the identified person.

---

# Security

Do not commit:

```text
.env
venv/
node_modules/
artifacts/
cache/
private keys
API keys
```

API credentials should always be stored in environment variables.

---

# Team

Team Texas Codem

Hacker House Goa 2026

---

# Quick Start

```powershell
git clone https://github.com/SaikiaMan/HHG-project.git
cd HHG-project

python -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r python/requirements.txt
npm install

npx hardhat node
```

In another terminal:

```powershell
cd D:\HHG\HHG-project
.\venv\Scripts\Activate.ps1

python python/demo.py --reset
```

Follow the terminal instructions and provide the input image when requested.

---

# Goal

The goal of HHG is to combine:

```text
Computer Vision
+
Real Web Search
+
Biometric Face Matching
+
Cryptographic Hashing
+
Blockchain Verification
```

into a single reproducible pipeline for online image provenance and integrity verification.
