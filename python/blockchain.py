import json
from web3 import Web3


RPC_URL = "http://127.0.0.1:8545"

CONTRACT_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3"

PRIVATE_KEY = (
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
)


# Connect to Hardhat
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise Exception("Could not connect to Hardhat")


# Load ABI
with open(
    "artifacts/contracts/PostVerification.sol/PostVerification.json"
) as f:
    contract_data = json.load(f)

abi = contract_data["abi"]


# Create contract instance
contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=abi,
)


# Use Hardhat account #0
account = w3.eth.account.from_key(PRIVATE_KEY)

print("Connected to blockchain")
print("Account:", account.address)
print("Contract:", CONTRACT_ADDRESS)


# Test hash
hash_hex = "98ffe7752af435438b6557a0a51f4b806db7ad33123fe5e2f25622adb592404b"

# Convert SHA-256 hex string to bytes32
hash_bytes = bytes.fromhex(hash_hex)


# Build transaction
transaction = contract.functions.storeHash(
    hash_bytes
).build_transaction({
    "from": account.address,
    "nonce": w3.eth.get_transaction_count(account.address),
    "gas": 200000,
    "gasPrice": w3.eth.gas_price,
})


# Sign transaction
signed_transaction = account.sign_transaction(transaction)


# Send transaction
tx_hash = w3.eth.send_raw_transaction(
    signed_transaction.raw_transaction
)

print("Transaction sent:", tx_hash.hex())


# Wait for confirmation
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

print("Transaction confirmed!")
print("Block:", receipt.blockNumber)


# Verify hash
verified = contract.functions.verifyHash(
    hash_bytes
).call()

print("Blockchain verification:", verified)