import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Tuple

# Ensure venv site-packages is in sys.path if running under system python
PROJECT_ROOT = Path(__file__).resolve().parent.parent
venv_site_packages = PROJECT_ROOT / "venv" / "Lib" / "site-packages"
if venv_site_packages.exists() and str(venv_site_packages) not in sys.path:
    sys.path.insert(0, str(venv_site_packages))

from web3 import Web3

RPC_URL = "http://127.0.0.1:8545"

ARTIFACT_PATH = PROJECT_ROOT / "artifacts" / "contracts" / "PostVerification.sol" / "PostVerification.json"
DEPLOYED_ADDRESS_FILE = PROJECT_ROOT / "python" / "contract_address.txt"

DEFAULT_CONTRACT_ADDRESS = "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"


def get_contract_address() -> str:
    """
    Returns the currently active deployed contract address.
    Checks python/contract_address.txt first, then environment variable, then default.
    """
    if DEPLOYED_ADDRESS_FILE.exists():
        try:
            addr = DEPLOYED_ADDRESS_FILE.read_text(encoding="utf-8").strip()
            if addr.startswith("0x") and len(addr) == 42:
                return addr
        except Exception:
            pass
    return os.getenv("CONTRACT_ADDRESS", DEFAULT_CONTRACT_ADDRESS)


def set_contract_address(address: str):
    """
    Persists the deployed contract address so all scripts stay in sync.
    """
    DEPLOYED_ADDRESS_FILE.write_text(address.strip(), encoding="utf-8")
    global CONTRACT_ADDRESS
    CONTRACT_ADDRESS = address.strip()


CONTRACT_ADDRESS = get_contract_address()


def hash_file(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def deploy_contract() -> str:
    """
    Deploys a fresh PostVerification smart contract instance to the running Hardhat node.
    Returns the newly deployed contract address and persists it.
    """
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise RuntimeError(f"Could not connect to Hardhat blockchain at {RPC_URL}")

    if not ARTIFACT_PATH.exists():
        raise FileNotFoundError(f"Contract artifact not found: {ARTIFACT_PATH}")

    with open(ARTIFACT_PATH, "r", encoding="utf-8") as f:
        contract_data = json.load(f)

    contract_factory = w3.eth.contract(
        abi=contract_data["abi"],
        bytecode=contract_data["bytecode"],
    )
    account = w3.eth.accounts[0]
    tx_hash = contract_factory.constructor().transact({"from": account})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    new_address = receipt.contractAddress
    set_contract_address(new_address)
    return new_address


def connect_blockchain(contract_address: str = None) -> Tuple[Web3, Any, str]:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))

    if not w3.is_connected():
        raise RuntimeError(f"Could not connect to Hardhat blockchain at {RPC_URL}")

    if not ARTIFACT_PATH.exists():
        raise FileNotFoundError(f"Contract artifact not found at {ARTIFACT_PATH}")

    with open(ARTIFACT_PATH, "r", encoding="utf-8") as f:
        contract_data = json.load(f)

    target_address = contract_address or get_contract_address()
    checksum_addr = Web3.to_checksum_address(target_address)

    # If connected to a fresh node instance where no code exists at target_address, auto-deploy
    try:
        code = w3.eth.get_code(checksum_addr)
    except Exception:
        code = b""

    if len(code) == 0 or code == b"\x00":
        target_address = deploy_contract()
        checksum_addr = Web3.to_checksum_address(target_address)

    contract = w3.eth.contract(
        address=checksum_addr,
        abi=contract_data["abi"],
    )

    account = w3.eth.accounts[0]
    return w3, contract, account


def register_content(file_path: str, contract_address: str = None) -> Dict[str, Any]:
    hash_hex = hash_file(file_path)
    hash_bytes = bytes.fromhex(hash_hex)

    w3, contract, account = connect_blockchain(contract_address)

    transaction = contract.functions.storeHash(
        hash_bytes
    ).build_transaction({
        "from": account,
        "nonce": w3.eth.get_transaction_count(account),
        "gas": 200000,
        "gasPrice": w3.eth.gas_price,
    })

    tx_hash = w3.eth.send_transaction(transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return {
        "file": str(file_path),
        "sha256": hash_hex,
        "transaction_hash": tx_hash.hex(),
        "block_number": receipt.blockNumber,
        "registered": True,
    }


def verify_content(file_path: str, contract_address: str = None) -> Dict[str, Any]:
    hash_hex = hash_file(file_path)
    hash_bytes = bytes.fromhex(hash_hex)

    _, contract, _ = connect_blockchain(contract_address)

    verified = contract.functions.verifyHash(
        hash_bytes
    ).call()

    return {
        "file": str(file_path),
        "sha256": hash_hex,
        "verified": verified,
    }


if __name__ == "__main__":
    print("REGISTERING ORIGINAL IMAGE")
    print("--------------------------------")

    registration = register_content("python/test.jpg")
    print(registration)

    print("\nVERIFYING ORIGINAL IMAGE")
    print("--------------------------------")

    original = verify_content("python/test.jpg")
    print(original)

    print("\nVERIFYING TAMPERED IMAGE")
    print("--------------------------------")

    tampered = verify_content("python/tampered.jpg")
    print(tampered)