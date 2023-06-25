from pathlib import Path
from bs4 import BeautifulSoup
import json
import toml

# Load config from config.toml
config = toml.load("config.toml")
PAYMENTS_DIR = config["amazon"]["payments_dir"]
ORDERS_DIR = config["amazon"]["orders_dir"]
AMAZON_TRANSACTIONS_FILE = config["amazon"]["transactions_file"]

# Get the absolute path of the HTML directories
PAYMENTS_DIR = Path(PAYMENTS_DIR).resolve()
ORDERS_DIR = Path(ORDERS_DIR).resolve()


def extract_text(element, default=None):
    """
    Extract stripped text from an element if it exists.
    """
    return element.get_text().strip() if element else default


def parse_transactions(soup_parser: BeautifulSoup) -> list[dict]:
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
        order_number = (
            extract_text(order_element).replace("Order #", "")
            if order_element
            else None
        )

        transactions.append({"amount": amount, "order_number": order_number})

    return transactions


def find_element_text(order_div, div_class, span_class) -> str:
    """
    Find an HTML element and return its text content.
    """
    element = order_div.find("div", class_=div_class).find("span", class_=span_class)
    return extract_text(element)


def parse_order(order_div) -> dict:
    """
    Parse order details from an HTML div.
    """
    order_placed = find_element_text(
        order_div, "a-column a-span3", "a-color-secondary value"
    )
    total = find_element_text(
        order_div, "a-column a-span2 yohtmlc-order-total", "a-color-secondary value"
    )
    ship_to = extract_text(order_div.find("span", class_="trigger-text"))

    order_id = find_element_text(
        order_div, "a-row a-size-mini yohtmlc-order-id", "a-color-secondary value"
    )

    # find all 'a' tags with class 'a-link-normal' in the soup
    links = order_div.find_all("a", {"class": "a-link-normal"})

    # filter out those that have '/product' in their 'href' attribute
    product_link = next(
        (
            link
            for link in links
            if ("/product" in link.get("href", "")) and link.text.strip()
        ),
        None,
    )

    description = extract_text(product_link).replace("\n", "") if product_link else None

    return {
        "date": order_placed,
        "amount": total,
        "ship_to": ship_to,
        "order_number": order_id,
        "description": description,
    }


def parse_orders(soup_parser: BeautifulSoup) -> list[dict]:
    """
    Parse orders from a HTML text.
    """
    order_divs = soup_parser.find_all(
        "div", class_="a-box-group a-spacing-base order js-order-card"
    )
    orders = [parse_order(div) for div in order_divs]
    return orders


def parse_html_files(directory_path: Path, parser_func):
    """
    Parse HTML files in a directory using a specified parser function.
    """
    parsed_items = []
    for file_path in directory_path.glob("*.htm*"):
        with open(file_path, "r", errors="ignore") as file:
            print("File Name:", file_path.name)
            html_content = file.read()
            parsed_items.extend(parser_func(BeautifulSoup(html_content, "html.parser")))

    return parsed_items


def main() -> None:
    """
    Main function to parse transactions and orders, combine them, and write to a JSON
    file.
    """
    transactions = parse_html_files(PAYMENTS_DIR, parse_transactions)
    orders = parse_html_files(ORDERS_DIR, parse_orders)

    # Combine orders and transactions by order number, ignoring orders without a
    # matching transaction.
    combined = [
        {**order, **transaction}
        for order in orders
        for transaction in transactions
        if order["order_number"] == transaction["order_number"]
    ]

    # Write the combined data to a JSON file
    with open(AMAZON_TRANSACTIONS_FILE, "w") as file:
        json.dump(combined, file, indent=4)


if __name__ == "__main__":
    main()
