import os
import time

from src.trading212.browser_utils import login_trading212, get_login_token
from src.trading212.trading212 import Trading212
from src.trading212.enums import OrderType, OrderStatus
from tests.conftest import clear_browser


TRADING212_URLS = ["https://live.trading212.com/", "https://demo.trading212.com/"]
TICKER = "MSFT"


def test_buy_order_workflow(driver):
    trading212 = Trading212()

    account_details = trading212.get_account_details()
    not_existing = float("-inf")
    cash_funds = account_details.get("cash", not_existing)
    total_funds = account_details.get("total", not_existing)
    assert cash_funds != not_existing and cash_funds > 0
    assert total_funds != not_existing and total_funds > 0

    equity = trading212.get_equity_data(TICKER)
    assert (isinstance(equity, dict) and equity.get("shortName", "") == "MSFT" and
            equity.get("objectID", "") == "MSFT_US_EQ")

    ask_price = trading212.get_ask_price(TICKER).get("price", not_existing)
    assert isinstance(ask_price, float) and ask_price > 0

    amount = 1.0
    costs_data = trading212.get_costs(OrderType.BUY, TICKER, amount)
    assert costs_data.get("orderQuantity", not_existing) > not_existing and costs_data.get("total") == amount

    order = trading212.place_order(OrderType.BUY, TICKER, amount)
    assert order.get("cost", {}).get("orderQuantity", not_existing) > not_existing
    order_id = order.get("orderId", "")

    observed_id_length = 10
    approx_length_diff = 3
    assert (
            order_id is not "" and
            observed_id_length + approx_length_diff > len(order_id) > observed_id_length - approx_length_diff
    )

    status = trading212.get_status(order_id)
    assert (status["status"] in OrderStatus.__members__.values() and
            status["status"] in [OrderStatus.SUBMITTED, OrderStatus.COMPLETED])

    if status["status"] == OrderStatus.SUBMITTED:
        print("Submitted")
        trading212.cancel_order(order_id)

    assert False

def _test_sell_order_workflow(driver):
    pass
    # Get account details.
    # Get equity data
    # Get ask price
    # Get costs
    # Sell equity
    # Check status
    # Check status
