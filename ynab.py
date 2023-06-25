import requests
from datetime import datetime, timedelta
import json
import toml


def get_default_budget_id() -> str:
    """Get the default budget ID from the YNAB API."""
    response = requests.get(
        "https://api.youneedabudget.com/v1/budgets",
        headers={"Authorization": f"Bearer {API_TOKEN}"},
    )
    response.raise_for_status()
    budgets = response.json()["data"]["budgets"]
    if not budgets:
        raise Exception("No budgets found.")
    return budgets[0]["id"]


# Load config from config.toml
config = toml.load("config.toml")

# Set to False to update YNAB transactions
DRY_RUN: bool = config["dry_run"]

# YNAB API Personal Access Token
API_TOKEN: str = config["ynab"]["api_token"]

# Budget ID to load transactions from
BUDGET_ID: str = config["ynab"].get("budget_id", get_default_budget_id())

# Cache file for YNAB transactions and API requests
YNAB_CACHE_FILE: str = config["ynab"]["cache_file"]

# File to load Amazon transactions from.  Output of amazon.py
AMAZON_TRANSACTIONS_FILE: str = config["amazon"]["transactions_file"]


def load_ynab_cache() -> dict:
    """Load transactions from cache file to reduce API load."""
    try:
        with open(YNAB_CACHE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"transactions": [], "server_knowledge": None}


def save_ynab_cache(ynab_data: dict) -> None:
    """Save transactions to cache file"""
    with open(YNAB_CACHE_FILE, "w") as f:
        json.dump(ynab_data, f)


def get_ynab_transactions() -> list[dict]:
    """
    Gets YNAB transactions.  First loads from cache file, then extends with new
    transactions from the API.
    """
    ynab_data: list[dict] = load_ynab_cache()

    # Get new transactions from API
    server_knowledge, new_transactions = get_new_ynab_transactions_from_api(
        ynab_data["server_knowledge"]
    )

    # Extend transactions with new transactions
    ynab_data["transactions"].extend(new_transactions)

    # Update server_knowledge
    ynab_data["server_knowledge"] = server_knowledge

    # Save transactions to cache file
    save_ynab_cache(ynab_data)

    return ynab_data["transactions"]


def get_new_ynab_transactions_from_api(
    server_knowledge: int | None,
) -> tuple[int, list[dict]]:
    """Get new transactions from YNAB API using a delta request if possible."""

    if server_knowledge:
        # Use server_knowledge to make delta requests for new transactions only
        url: str = f"https://api.youneedabudget.com/v1/budgets/{BUDGET_ID}/transactions?last_knowledge_of_server={server_knowledge}"  # noqa: E501
    else:
        url: str = f"https://api.youneedabudget.com/v1/budgets/{BUDGET_ID}/transactions"  # noqa: E501

    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {API_TOKEN}"},
    )
    response.raise_for_status()

    server_knowledge = int(response.json()["data"]["server_knowledge"])
    new_transactions = response.json()["data"]["transactions"]

    return server_knowledge, new_transactions


def update_transaction(transaction_id: str, memo: str) -> None:
    print(f"Updating transaction {transaction_id} with memo: {memo}")
    if DRY_RUN:
        print(f"Would update transaction {transaction_id} with memo: {memo}")
    else:
        response = requests.patch(
            f"https://api.youneedabudget.com/v1/budgets/{BUDGET_ID}/transactions",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            json={"transactions": [{"id": transaction_id, "memo": memo}]},
        )
        print("Success") if response.ok else print("Failed")
        response.raise_for_status()


def get_date_range(date: str) -> tuple[datetime, datetime]:
    parsed_date = datetime.strptime(date, "%B %d, %Y")
    start_date = parsed_date - timedelta(days=3)
    end_date = parsed_date + timedelta(days=3)
    return start_date, end_date


def is_within_date_range(
    ynab_date: str, start_date: datetime, end_date: datetime
) -> bool:
    ynab_date_obj = datetime.strptime(ynab_date, "%Y-%m-%d")
    return start_date <= ynab_date_obj <= end_date


def match_and_update(
    amazon_transactions: list[dict], ynab_transactions: list[dict]
) -> None:
    for amazon_transaction in amazon_transactions:
        start_date, end_date = get_date_range(amazon_transaction["date"])
        amount_in_milliunits = int(
            float(amazon_transaction["amount"].replace("$", "")) * 1000
        )

        for ynab_transaction in ynab_transactions:
            if (
                is_within_date_range(ynab_transaction["date"], start_date, end_date)
                and ynab_transaction["amount"] == amount_in_milliunits
            ):
                update_transaction(
                    ynab_transaction["id"], amazon_transaction["description"]
                )


def main():
    try:
        amazon_transactions = json.load(open(AMAZON_TRANSACTIONS_FILE, "r"))
    except FileNotFoundError:
        print("No transactions found.  Did you run amazon.py?")
        return

    ynab_transactions = get_ynab_transactions()

    match_and_update(amazon_transactions, ynab_transactions)


if __name__ == "__main__":
    main()
