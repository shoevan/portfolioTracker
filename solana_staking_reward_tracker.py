import argparse
import asyncio
from typing import List, Optional, Dict, Union
from datetime import datetime, timezone
import requests  # For fetching AUD exchange rate

from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import MemcmpOpts
from solana.exceptions import SolanaRpcException
from yaml import dump, safe_load
from dotenv import load_dotenv
from os import getenv

# Constants
STAKE_PROGRAM_ID = Pubkey.from_string(
    "Stake11111111111111111111111111111111111111")
WITHDRAWER_AUTHORITY_OFFSET = 44
STAKE_ACCOUNT_DATA_SIZE = 200
LAMPORTS_PER_SOL = 1_000_000_000
COINGECKO_HISTORY_API_URL = "https://api.coingecko.com/api/v3/coins/solana/history?date={date}"
# Delay between new historical API calls (in seconds) to avoid rate limits
COINGECKO_API_DELAY = 2


def lamports_to_sol(lamports: int) -> float:
    """Converts lamports to SOL."""
    return lamports / LAMPORTS_PER_SOL


def format_timestamp(unix_timestamp: Optional[int]) -> str:
    """Converts a Unix timestamp to a human-readable UTC string."""
    if unix_timestamp is None:
        return "N/A"
    try:
        return datetime.fromtimestamp(unix_timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception:
        return "Invalid Timestamp"


async def get_historical_sol_aud_rate(date_str: str) -> Optional[float]:
    """Fetches historical SOL to AUD rate for a specific date (dd-mm-yyyy)."""
    api_url = COINGECKO_HISTORY_API_URL.format(date=date_str)
    try:
        print(f"      Fetching historical rate for {date_str}...")
        # Increased timeout for potentially slower history API
        response = await asyncio.to_thread(requests.get, api_url, timeout=15)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        rate = data.get("market_data", {}).get("current_price", {}).get("aud")
        if rate is not None:
            print(f"      -> Rate for {date_str}: {rate:.2f} AUD")
            return float(rate)
        else:
            print(
                f"      Warning: Could not find historical AUD rate for {date_str} in response.")
            return None
    except requests.exceptions.RequestException as e:
        print(
            f"      Warning: Could not fetch historical rate for {date_str}: {e}")
        return None
    except (ValueError, KeyError, requests.exceptions.JSONDecodeError) as e:
        print(
            f"      Warning: Error parsing historical response for {date_str}: {e}")
        return None


async def get_staking_rewards(wallet_address: str, rpc_url: str, epochs_to_check: int):
    """
    Retrieves staking rewards for a given Solana wallet address, with historical AUD conversion.
    """
    print(
        f"Attempting to retrieve staking rewards for wallet: {wallet_address}")
    print(f"Using RPC URL: {rpc_url}")
    print(f"Checking the last {epochs_to_check} epochs.\n")
    with open(file="staking_rewards.yaml") as fp:
        staking_rewards = safe_load(stream=fp)
    try:
        user_pubkey = Pubkey.from_string(wallet_address)
    except ValueError:
        print(f"Error: Invalid wallet address format: {wallet_address}")
        return

    # Cache for historical rates: { 'dd-mm-yyyy': rate | None }
    date_to_aud_rate_cache: Dict[str, Optional[float]] = {}
    aud_conversion_possible = True  # Track if all conversions were successful

    async with AsyncClient(rpc_url, commitment=Confirmed) as client:
        try:
            is_healthy = await client.is_connected()
            if not is_healthy:
                print("Error: Failed to connect to the Solana RPC endpoint.")
                return
            print("Successfully connected to RPC endpoint.")

            print(
                f"\nSearching for stake accounts where {user_pubkey} is the withdrawer authority...")
            filters = [
                MemcmpOpts(offset=WITHDRAWER_AUTHORITY_OFFSET,
                           bytes=str(user_pubkey)),
            ]

            response = await client.get_program_accounts(
                STAKE_PROGRAM_ID,
                commitment=Confirmed,
                encoding="base64",
                filters=filters
            )

            stake_accounts_info = response.value
            if not stake_accounts_info:
                print(
                    f"No stake accounts found where {user_pubkey} is the withdrawer authority.")
                return

            stake_account_pubkeys: List[Pubkey] = [
                acc.pubkey for acc in stake_accounts_info]
            print(f"Found {len(stake_account_pubkeys)} stake account(s):")
            for pk in stake_account_pubkeys:
                print(f"- {pk}")

            print("\nFetching current epoch information...")
            epoch_info_res = await client.get_epoch_info(commitment=Confirmed)
            current_epoch = epoch_info_res.value.epoch
            print(f"Current epoch: {current_epoch}")

            total_rewards_lamports = 0
            total_rewards_aud = 0.0
            rewards_by_epoch: Dict[int, Dict[str, Dict[str,
                                                       Union[int, float, Optional[int], Optional[float]]]]] = {}
            start_epoch = max(0, current_epoch - epochs_to_check + 1)

            print(
                f"\nFetching rewards from epoch {start_epoch} to {current_epoch}...")
            for epoch_num in range(start_epoch, current_epoch + 1):
                print(f"  Checking epoch {epoch_num}...")
                if epoch_num in staking_rewards.keys():
                    continue
                try:
                    rewards_res = await client.get_inflation_reward(
                        pubkeys=stake_account_pubkeys,
                        epoch=epoch_num,  # type: ignore
                        commitment=Confirmed
                    )

                    epoch_rewards_lamports = 0
                    rewards_by_epoch[epoch_num] = {}

                    for i, reward_info in enumerate(rewards_res.value):
                        stake_acc_pk_str = str(stake_account_pubkeys[i])
                        if reward_info:
                            amount_lamports = reward_info.amount
                            amount_sol = lamports_to_sol(amount_lamports)
                            effective_slot = reward_info.effective_slot
                            amount_aud: Optional[float] = None

                            timestamp_unix: Optional[int] = None
                            try:
                                block_time_res = await client.get_block_time(effective_slot)
                                if block_time_res.value is not None:
                                    timestamp_unix = block_time_res.value
                            except Exception as e:
                                print(
                                    f"      Warning: Could not fetch block time for slot {effective_slot}: {e}")

                            # Fetch/Cache historical rate if timestamp is available
                            if timestamp_unix:
                                dt_object = datetime.fromtimestamp(
                                    timestamp_unix, timezone.utc)
                                date_key = dt_object.strftime(
                                    '%d-%m-%Y')  # CoinGecko format

                                if date_key not in date_to_aud_rate_cache:
                                    rate = await get_historical_sol_aud_rate(date_key)
                                    date_to_aud_rate_cache[date_key] = rate
                                    # Add delay *only* when a new API call is made
                                    await asyncio.sleep(COINGECKO_API_DELAY)
                                else:
                                    rate = date_to_aud_rate_cache[date_key]

                                if rate is not None:
                                    amount_aud = amount_sol * rate
                                    total_rewards_aud += amount_aud
                                else:
                                    aud_conversion_possible = False  # Mark total AUD as incomplete
                            else:
                                aud_conversion_possible = False  # Mark total AUD as incomplete

                            rewards_by_epoch[epoch_num][stake_acc_pk_str] = {
                                'amount_lamports': amount_lamports, 'amount_sol': amount_sol,
                                'amount_aud': amount_aud, 'slot': effective_slot,
                                'timestamp': timestamp_unix
                            }
                            epoch_rewards_lamports += amount_lamports
                            total_rewards_lamports += amount_lamports

                            aud_str = f" (~{amount_aud:.2f} AUD Hist.)" if amount_aud is not None else " (AUD N/A)"
                            print(f"    - Account {stake_acc_pk_str}: {amount_sol:.9f} SOL{aud_str} "
                                  f"(Time: {format_timestamp(timestamp_unix)})")
                            staking_rewards[epoch_num] = {}
                            staking_rewards[epoch_num]["Amount"] = amount_sol
                            staking_rewards[epoch_num]["Timestamp Unix"] = timestamp_unix
                        else:
                            rewards_by_epoch[epoch_num][stake_acc_pk_str] = {
                                'amount_lamports': 0, 'amount_sol': 0.0, 'amount_aud': None,
                                'slot': 0, 'timestamp': None
                            }
                            print(
                                f"    - Account {stake_acc_pk_str}: No reward found for this epoch.")

                    if epoch_rewards_lamports == 0 and not any(rewards_res.value):
                        print(
                            f"    No rewards found for any account in epoch {epoch_num}.")

                except SolanaRpcException as e:
                    print(
                        f"    Error fetching rewards for epoch {epoch_num}: {e}")
                except Exception as e:
                    print(
                        f"    An unexpected error occurred fetching rewards for epoch {epoch_num}: {e}")

            # 5. Display results
            print("\n--- Summary ---")
            if not rewards_by_epoch:
                print("No reward information found for the checked epochs.")
            else:
                for epoch, rewards_data in rewards_by_epoch.items():
                    print(f"\nEpoch {epoch}:")
                    # type: ignore
                    if not rewards_data or all(details['amount_lamports'] == 0 for details in rewards_data.values()):
                        print(
                            "  No rewards credited in this epoch for the found stake accounts.")
                        continue
                    for acc_pk_str, details in rewards_data.items():
                        amount_sol = details['amount_sol']
                        amount_aud = details['amount_aud']  # type: ignore
                        timestamp_unix = details['timestamp']  # type: ignore

                        if amount_sol > 0:  # type: ignore
                            aud_str = f" (~{amount_aud:.2f} AUD Hist.)" if amount_aud is not None else " (AUD N/A)"
                            print(f"  - Account {acc_pk_str}: {amount_sol:.9f} SOL{aud_str} "  # type: ignore
                                  f"(Time: {format_timestamp(timestamp_unix)})")
                            
                        else:
                            print(
                                f"  - Account {acc_pk_str}: No reward / Not applicable")

            total_rewards_sol = lamports_to_sol(total_rewards_lamports)
            total_rewards_aud_str = ""
            if aud_conversion_possible and total_rewards_aud > 0:
                total_rewards_aud_str = f" (~{total_rewards_aud:.2f} AUD Historical Est.)"
            elif total_rewards_sol > 0:
                total_rewards_aud_str = " (AUD Historical Est. Incomplete/Unavailable)"

            print(
                f"\nTotal native staking rewards found across {len(stake_account_pubkeys)} account(s) for epochs {start_epoch}-{current_epoch}:")
            print(f"{total_rewards_sol:.9f} SOL{total_rewards_aud_str}")
        except SolanaRpcException as e:
            print(f"\nAn RPC error occurred: {e}")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
        finally:
            with open(file="results/staking_rewards.yaml", mode="w") as fp:
                dump(data=staking_rewards, stream=fp)

    print("\n--- Disclaimer ---")
    print("This script attempts to retrieve rewards from NATIVE SOL STAKING only.")
    print("AUD values are estimates based on DAILY HISTORICAL data from CoinGecko (UTC) and are for informational purposes only.")
    print("Actual received value may differ. API calls are delayed to respect rate limits - this script may run slowly.")
    print("This script is for informational purposes only and is not financial advice.")
    print("Ensure you have the 'solana' and 'requests' Python libraries installed (`pip install solana requests`).")


async def main():
    parser = argparse.ArgumentParser(
        description="Retrieve Solana native staking rewards for a wallet address, with historical AUD conversion.")
    parser.add_argument("wallet_address", type=str,
                        help="Your Solana wallet public key.")
    parser.add_argument(
        "--rpc_url",
        type=str,
        default="https://api.mainnet-beta.solana.com",
        help="Solana RPC endpoint URL. (Defaults to mainnet-beta)"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=308,  # Further reduced default due to historical API calls
        help="Number of recent epochs to check for rewards. (Defaults to 2)"
    )
    load_dotenv()
    args = parser.parse_args()

    if args.epochs <= 0:
        print("Error: Number of epochs to check must be positive.")
        return
    wallet_address = getenv(key="SOLANA_WALLET_ADDRESS")
    await get_staking_rewards(wallet_address, args.rpc_url, args.epochs)

if __name__ == "__main__":
    asyncio.run(main())
