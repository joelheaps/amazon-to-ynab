import pytest
from bs4 import BeautifulSoup
from unittest.mock import Mock, call

# assuming parse_orders and parse_order are in a module named 'module'
from amazon import parse_orders, parse_order


def test_parse_orders(monkeypatch):
    # Mock BeautifulSoup.find_all
    mock_find_all = Mock(return_value=["div1", "div2", "div3"])
    monkeypatch.setattr(BeautifulSoup, "find_all", mock_find_all)

    # Mock parse_order
    mock_parse_order = Mock(side_effect=["order1", "order2", "order3"])
    monkeypatch.setattr("amazon.parse_order", mock_parse_order)

    # Create a BeautifulSoup object
    soup_parser = BeautifulSoup("", "html.parser")

    # Call parse_orders
    orders = parse_orders(soup_parser)

    # Verify find_all was called with correct arguments
    mock_find_all.assert_called_once_with(
        "div", class_="a-box-group a-spacing-base order js-order-card"
    )

    # Verify parse_order was called with correct arguments
    mock_parse_order.assert_has_calls([call("div1"), call("div2"), call("div3")])

    # Verify parse_orders return value
    assert orders == ["order1", "order2", "order3"]
