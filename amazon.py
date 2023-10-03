from pathlib import Path
from bs4 import BeautifulSoup
from bs4 import Tag
import json
import toml
import logging
import sys
from pydantic import BaseModel
from typing import Callable, Any

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

# Load config from config.toml
config = toml.load("config.toml")
PAYMENTS_DIR = config["amazon"]["payments_dir"]
ORDERS_DIR = config["amazon"]["orders_dir"]
AMAZON_TRANSACTIONS_FILE = config["amazon"]["transactions_file"]

# Get the absolute path of the HTML directories
PAYMENTS_DIR = Path(PAYMENTS_DIR).resolve()
ORDERS_DIR = Path(ORDERS_DIR).resolve()


class Transaction(BaseModel):
    amount: str
    order_number: str


class Order(BaseModel):
    date: str
    subtotal: str
    order_number: str
    description: str | None = None  # Optional description field
    transaction_amount: int = 0  # Cents


def extract_text(element, default="") -> str:
    """
    Extract stripped text from an element if it exists.
    """
    return element.get_text().strip() if element else default


def parse_transactions(soup_parser: BeautifulSoup) -> list[Transaction]:
    """
    Parse transaction details from a BeautifulSoup object.
    """
    transaction_parsers = soup_parser.find_all(
        class_="apx-transactions-line-item-component-container"
    )

    transactions = []
    for parser in transaction_parsers:
        amount_element = parser.find(class_="a-size-base-plus a-text-bold")
        amount = extract_text(amount_element)

        order_element = parser.find("a")
        order_number = extract_text(order_element).replace("Order #", "")

        transactions.append(Transaction(amount=amount, order_number=order_number))

    return transactions


def parse_order(order_div: Tag) -> Order:
    logging.info("Parsing a new order div...")

    # Extracting the date
    date = order_div.find("span", class_="a-size-base a-color-secondary")
    date = date.text if date else ""
    logging.debug(f"Extracted order date: {date}")

    # Extracting the subtotal
    subtotal = order_div.find("div", class_="yohtmlc-order-total")
    subtotal = subtotal.text.strip() if subtotal else ""
    logging.debug(f"Extracted order subtotal: {subtotal}")

    # Extracting order number (ID)
    order_number_section = order_div.find("span", string="Order #")
    order_number = (
        order_number_section.find_next_sibling("span") if order_number_section else None
    )
    order_number = order_number.text.strip() if order_number else ""
    logging.debug(f"Extracted order number: {order_number}")

    # Extracting the description
    description_div = order_div.find("div", class_="yohtmlc-product-title")
    description = description_div.text.strip() if description_div else None
    if description:
        logging.debug(f"Extracted product description: {description}")
    else:
        logging.warning("No product description found for this order.")

    # Constructing the Order object
    order = Order(
        date=date,
        subtotal=subtotal,
        order_number=order_number,
        description=description,
    )

    logging.info("Order parsing complete.")

    return order


def parse_orders(soup_parser: BeautifulSoup) -> list[Order]:
    """
    Parse orders from a HTML text.
    """
    logging.info("Starting the parsing of orders...")

    order_divs = soup_parser.find_all("div", class_="order-card js-order-card")

    if not order_divs:
        logging.warning("No order divs found in the provided content!")
        return []

    logging.debug(f"Found {len(order_divs)} order divs to process.")

    orders = [parse_order(div) for div in order_divs]

    logging.info(f"Parsed a total of {len(orders)} orders.")

    return orders


def parse_html_files(
    directory_path: Path, parser_func: Callable[[BeautifulSoup], Any]
) -> Any:
    """
    Parse HTML files in a directory using a specified parser function.
    """
    parsed_items = []
    for file_path in directory_path.glob("*.htm*"):
        with open(file_path, "r", errors="ignore") as file:
            logging.info(f"Parsing HTML file: {file_path.name}")
            html_content = file.read()
            parsed_items.extend(parser_func(BeautifulSoup(html_content, "html.parser")))

    return parsed_items


def associate_transactions_to_orders(
    transactions: list[Transaction], orders: list[Order]
) -> list[Order]:
    """
    Associate transaction amounts to orders based on order number.
    Returns a list of orders with the associated transaction amounts.
    """
    # Dictionary to hold transactions by order number
    transaction_dict = {
        transaction.order_number: transaction for transaction in transactions
    }

    for order in orders:
        transaction = transaction_dict.get(order.order_number)
        if transaction:
            # Convert the transaction amount from string to integer (in cents)
            # for consistency
            cents = int(float(transaction.amount.replace("$", "")) * 100)
            order.transaction_amount = cents

    # Log the results
    logging.info("Total transactions: %d", len(transactions))
    logging.info("Total orders: %d", len(orders))
    logging.info(
        "Number of orders with associated transactions: %d",
        sum(1 for order in orders if order.transaction_amount > 0),
    )

    return orders


def main() -> None:
    """
    Main function to parse transactions and orders, combine them, and write to a JSON
    file.
    """
    transactions = parse_html_files(PAYMENTS_DIR, parse_transactions)
    orders = parse_html_files(ORDERS_DIR, parse_orders)

    # Combine orders and transactions by order number, ignoring orders without a
    # matching transaction.
    orders_with_totals: list[Order] = associate_transactions_to_orders(
        transactions, orders
    )
    json_ready_orders: list[dict] = [model.model_dump() for model in orders_with_totals]

    # Write the combined data to a JSON file
    with open(AMAZON_TRANSACTIONS_FILE, "w") as file:
        json.dump(json_ready_orders, file, indent=4)


if __name__ == "__main__":
    main()
