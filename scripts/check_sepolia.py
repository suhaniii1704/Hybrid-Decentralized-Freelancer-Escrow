
import os
import json
import urllib.request
from decimal import Decimal
from dotenv import load_dotenv
from eth_account import Account

load_dotenv()

RPC_URL = os.getenv("BASE_SEPOLIA_RPC_URL")
PRIVATE_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")

if not RPC_URL or not PRIVATE_KEY:
    raise SystemExit(
        "Missing BASE_SEPOLIA_RPC_URL or DEPLOYER_PRIVATE_KEY in .env"
    )

def rpc_call(method, params=None):
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }).encode()

    request = urllib.request.Request(
        RPC_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode())

    if "error" in result:
        raise RuntimeError(f"RPC error: {result['error']}")

    return result["result"]

try:
    chain_id = int(rpc_call("eth_chainId"), 16)
    block_number = int(rpc_call("eth_blockNumber"), 16)
    account = Account.from_key(PRIVATE_KEY)
    balance_wei = int(
        rpc_call("eth_getBalance", [account.address, "latest"]), 16
    )
    balance_eth = Decimal(balance_wei) / Decimal(10**18)

    print(f"Connected: Yes")
    print(f"Chain ID: {chain_id}")
    print(f"Latest block: {block_number}")
    print(f"Deployer address: {account.address}")
    print(f"Deployer balance: {balance_eth} ETH")

    if chain_id != 84532:
        raise SystemExit("ERROR: RPC is not connected to Base Sepolia.")

    if balance_wei == 0:
        print("WARNING: Wallet has no test ETH yet.")
        print("Get Base Sepolia ETH before attempting deployment.")
    else:
        print("Preflight passed. Wallet has test ETH.")

except Exception as exc:
    raise SystemExit(
        f"Connection check failed: {type(exc).__name__}: {exc}"
    )