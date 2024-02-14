import time

from tradingTOT.tradingTOT import tradingTOT
from tradingTOT.enums import OrderType, OrderStatus, FailureTypes
from tradingTOT.exceptions import BrokerOrderError
from tradingTOT.utils import VALUE_UNAVAILABLE

TRADINGTOT_URLS = ["https://live.trading212.com/", "https://demo.trading212.com/"]
TICKER = "MSFT"


def test_buy_order_workflow(driver):
    tradingtot = tradingTOT()

    account_details = tradingtot.get_account_details()
    cash_funds = account_details.get("cash", VALUE_UNAVAILABLE)
    total_funds = account_details.get("total", VALUE_UNAVAILABLE)
    assert cash_funds != VALUE_UNAVAILABLE and cash_funds > 0
    assert total_funds != VALUE_UNAVAILABLE and total_funds > 0

    equity = tradingtot.get_equity_data(TICKER)
    assert (isinstance(equity, dict) and equity.get("shortName", "") == "MSFT" and
            equity.get("objectID", "") == "MSFT_US_EQ")

    ask_price = tradingtot.get_ask_price(TICKER).get("price", -VALUE_UNAVAILABLE)
    assert isinstance(ask_price, float) and ask_price > 0

    amount = 1.0
    costs_data = tradingtot.get_costs(OrderType.BUY, TICKER, amount)
    assert costs_data.get("orderQuantity", -VALUE_UNAVAILABLE) > -VALUE_UNAVAILABLE and costs_data.get("total") == amount

    order = tradingtot.place_order(OrderType.BUY, TICKER, amount)
    assert order.get("cost", {}).get("orderQuantity", -VALUE_UNAVAILABLE) > -VALUE_UNAVAILABLE
    order_id = order.get("orderId", "")

    observed_id_length = 10
    approx_length_diff = 3
    assert (
            order_id is not "" and
            observed_id_length + approx_length_diff > len(order_id) > observed_id_length - approx_length_diff
    )

    status = tradingtot.get_status(order_id)
    assert status["status"] in [OrderStatus.SUBMITTED, OrderStatus.COMPLETED]

    if status["status"] == OrderStatus.SUBMITTED:
        tradingtot.cancel_order(order_id)


def test_sell_order_workflow(driver):
    tradingtot = tradingTOT()

    # TODO: Test for too small
    # TODO: Test for precision more than 2 e.g 1.24353546 instead of 1.24
    too_big_amount = 10000
    try:
        tradingtot.place_order(OrderType.SELL, ticker=TICKER, amount=too_big_amount)
    except BrokerOrderError as e:
        expected_reason = FailureTypes.InsufficientValueForStocksSell
        assert expected_reason.lower() in e.args[0].lower()

    position = tradingtot.get_position(TICKER)
    sell_amount = 1.0
    equity_exists = True
    if sell_amount > position["quantity"] * position["currentPrice"]:
        # Increasing trade amount before buying in cases where the price drops before sale.
        buy_amount = sell_amount + 0.5
        order = tradingtot.place_order(OrderType.BUY, ticker=TICKER, amount=buy_amount)
        order_id = order["orderId"]
        status = tradingtot.get_status(order_id)["status"]
        assert status["status"] in [OrderStatus.SUBMITTED, OrderStatus.COMPLETED]

        retries = 5
        while status is OrderStatus.SUBMITTED and status is not OrderStatus.COMPLETED:
            time.sleep(5)
            status = tradingtot.get_status(order_id)["status"]
            retries -= 1
            if not retries:
                break

        if status is OrderStatus.SUBMITTED:
            equity_exists = False
            tradingtot.cancel_order(order_id)

    # TODO: Log here so we know when remaining tests are run.
    if not equity_exists:
        return

    order = tradingtot.place_order(OrderType.SELL, ticker=TICKER, amount=sell_amount)
    assert order.get("cost", {}).get("orderQuantity", VALUE_UNAVAILABLE) < VALUE_UNAVAILABLE

    order_id = order.get("orderId", "")
    status = tradingtot.get_status(order_id)
    assert status["status"] in [OrderStatus.SUBMITTED, OrderStatus.COMPLETED]

    if status["status"] == OrderStatus.SUBMITTED:
        tradingtot.cancel_order(order_id)
