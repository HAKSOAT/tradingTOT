from collections import defaultdict

import pytest

from src.trading121.trading212 import Trading212
from src.trading121.enums import OrderType, OrderStatus
from src.trading121.constants import VALUE_UNAVAILABLE

TRADING212_URLS = ["https://live.trading212.com/", "https://demo.trading212.com/"]
TICKER = "MSFT"

FUNC_STATE = defaultdict(dict)


@pytest.mark.order(1)
def test_buy_order_workflow(driver):
    trading212 = Trading212()

    account_details = trading212.get_account_details()
    cash_funds = account_details.get("cash", VALUE_UNAVAILABLE)
    total_funds = account_details.get("total", VALUE_UNAVAILABLE)
    assert cash_funds != VALUE_UNAVAILABLE and cash_funds > 0
    assert total_funds != VALUE_UNAVAILABLE and total_funds > 0

    equity = trading212.get_equity_data(TICKER)
    assert (isinstance(equity, dict) and equity.get("shortName", "") == "MSFT" and
            equity.get("objectID", "") == "MSFT_US_EQ")

    ask_price = trading212.get_ask_price(TICKER).get("price", -VALUE_UNAVAILABLE)
    assert isinstance(ask_price, float) and ask_price > 0

    amount = 1.0
    costs_data = trading212.get_costs(OrderType.BUY, TICKER, amount)
    assert costs_data.get("orderQuantity", -VALUE_UNAVAILABLE) > -VALUE_UNAVAILABLE and costs_data.get("total") == amount

    order = trading212.place_order(OrderType.BUY, TICKER, amount)
    assert order.get("cost", {}).get("orderQuantity", -VALUE_UNAVAILABLE) > -VALUE_UNAVAILABLE
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
        trading212.cancel_order(order_id)
        FUNC_STATE[test_buy_order_workflow.__name__][order_id] = {"status": OrderStatus.SUBMITTED}
    else:
        FUNC_STATE[test_buy_order_workflow.__name__][order_id] = {"status": OrderStatus.COMPLETED}


# Running this immediately (i.e. order=2) after `test_buy_order_workflow` because
# selling equities depends on buying equities.
@pytest.mark.order(2)
def _test_sell_order_workflow(driver):
    order_ids = FUNC_STATE[test_buy_order_workflow.__name__]
    state = FUNC_STATE[test_buy_order_workflow.__name__].pop(order_ids[0])






    # Check if order was completed in previous tests.
    # Check amount of stocks available in the equity
    # Get equity data
    # Get ask price
    # Get sell costs
    # Try selling more than exists
    # Try selling what was bought if completed
    # Check status
    # Check status
