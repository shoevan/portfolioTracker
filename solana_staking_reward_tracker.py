from solders.pubkey import Pubkey
from solders.rpc.config import RpcAccountInfoConfig
from solders.rpc.responses import GetAccountInfoResp
from solders.rpc.requests import GetTokenAccountsByOwner
import time
import json
from solana.rpc.api import Client
from solana.publickey import PublicKey
import asyncio
import json
import time

import asyncio
from solana.rpc.async_api import AsyncClient

# Replace with your desired wallet address
wallet_address = "G9ZWFQkfotRZad5sKLsNarzsZr9Zgv9NDChMGjHE3k3k"  # Example: "YOUR_WALLET_ADDRESS_HERE"

# Replace with your RPC endpoint (or leave as default for devnet)
rpc_endpoint = "https://api.devnet.solana.com" # Example: "https://api.mainnet-beta.solana.com"

# Initialize the RPC client




# ... (wallet_address and rpc_endpoint as before)

async def get_staking_rewards(wallet_address: str) -> dict:
    try:
        client = Client(rpc_endpoint)  # Create a regular (synchronous) client

        pubkey = PublicKey(wallet_address)
        accounts = client.get_token_accounts_by_owner(pubkey)

        rewards = {}
        for account in accounts["value"]:
            account_pubkey = PublicKey(account["pubkey"])
            account_info = client.get_account_info(str(account_pubkey), encoding="jsonParsed")

            if account_info["result"] and account_info["result"]["value"] and account_info["result"]["value"]["data"] and "parsed" in account_info["result"]["value"]["data"] and "account" in account_info["result"]["value"]["data"]["parsed"]:
                account_data = account_info["result"]["value"]["data"]["parsed"]["account"]

                if "stake" in account_data and "delegation" in account_data["stake"]:
                    stake_info = account_data['stake']
                    delegation_info = stake_info['delegation']
                    voter_address = delegation_info['voter']
                    staked_balance = account_info["result"]["value"]["lamports"]
                    rewards[str(account_pubkey)] = {"staked_balance": staked_balance, "voter_address": voter_address}

        return rewards

    except Exception as e:
        print(f"Error: {e}")
        return {}


async def main():
    while True:
        rewards_data = await asyncio.to_thread(get_staking_rewards, wallet_address)  # Run in a separate thread

        if rewards_data:
            print(json.dumps(rewards_data, indent=4))
        else:
            print("No staking accounts found or error occurred.")

        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())