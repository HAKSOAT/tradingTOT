from threading import Lock
from typing import Union, Dict, Optional, Set, List

from requests.sessions import Session

from trading121.schemas.api_responses import Position, SummarySchema
from trading121.exceptions import BrokerOrderError
from trading121.endpoints import (VALIDATE_URL, PLACE_ORDER_URL,
                        ORDER_COSTS_URL, TICKER_PRICE_URL, ACCOUNT_SUMMARY_URL,
                        ORDER_HISTORY, ALGOLIA_CONFIG_URL, ALGOLIA_SEARCH_URL)
from trading121.enums import OrderStatus, OrderType

from trading121.existing_orders import ExistingOrdersHandler
from trading121.utils.browser_utils import enforce_auth


# The value is randomly chosen as I am yet to observe an increment more than that.
FILLID_MAX_INCREMENT = 50

SUPPORTED_EXCHANGES = {"NASDAQ", "NYSE"}


class Trading212:
    def __init__(self, session: Optional[Session] = None):
        """
        Main class for executing Trading212 functionality.

        Args:
            session: Requests Session.
        """
        if not session:
            session = Session()

        self.session = session
        self.order_lock = Lock()
        self.algolia_credentials = {"applicationId": None, "searchApiKey": None}
        self.ticker_to_object_id = {}
        self.object_id_to_ticker = {}

    @enforce_auth
    def place_order(self, action: Union[OrderType, str], ticker: str, amount: Union[float, int]) -> Dict:
        """
        Places an order.

        Args:
            action: Order type
            ticker: Ticker to trade
            amount: The amount (currency not share quantity) to be used in the transaction.

        Returns:

        """
        if action == "BUY":
            amount = abs(amount)
        elif action == "SELL":
            amount = -abs(amount)
        else:
            raise Exception("Order action not supported.")

        object_id = self._get_object_id(ticker)
        payload = {"currency":"GBP","instrumentCode":object_id,"orderType":"MARKET",
                   "value":amount,"timeValidity":"GOOD_TILL_CANCEL"}

        response = self.session.post(VALIDATE_URL, json=payload)

        # Trading212 returns empty string if valid
        if not response.content:
            with self.order_lock:
                order_handler = ExistingOrdersHandler(self.session)
                existing_orders = order_handler.from_summary()
                order_ids = {order.get("orderId") for order in existing_orders}
                response = self.session.post(PLACE_ORDER_URL, json=payload)
                existing_orders = order_handler.from_execution_response(response=response)
                for order in existing_orders:
                    if not (order["orderId"] not in order_ids and order.get("code") == object_id
                            and order.get("value") == amount):
                        continue

                    order["cost"] = self.get_costs(action, object_id, amount)
                    return order
        else:
            raise BrokerOrderError(f"The order was invalid. Reason: {response.content}")

        return response.json()

    @enforce_auth
    def cancel_order(self, order_id: Union[int, str]) -> Dict:
        """Cancel a Trading212 order.

        Args:
            order_id: Order id.

        Returns:
            Response from cancel attempt.
        """
        url = f"{PLACE_ORDER_URL}/{order_id}"
        response = self.session.delete(url)
        return response.json()


    @enforce_auth
    def get_costs(self, action: OrderType, ticker, amount) -> Dict:
        """Analyze an order action and return the costs of executing the order action.

        Args:
            action: OrderType action.
            ticker: Ticker symbol.
            amount: The amount (currency not share quantity) to be used in the transaction.

        Returns:
            Costs data.
        """
        if action == OrderType.BUY:
            amount = abs(amount)
        elif action == OrderType.SELL:
            amount = -abs(amount)
        else:
            raise Exception("Order action not supported.")

        object_id = self._get_object_id(ticker)
        payload = {"currency":"GBP","instrumentCode": object_id, "orderType":"MARKET",
                   "value":amount,"timeValidity":"GOOD_TILL_CANCEL"}
        response = self.session.post(ORDER_COSTS_URL, json=payload)
        return response.json()

    @enforce_auth
    def _get_algolia_credentials(self) -> Dict:
        """Fetches Trading212 algolia credentials

        Returns:
            Algolia credentials.
        """
        response = self.session.get(ALGOLIA_CONFIG_URL).json()
        self.algolia_credentials["applicationId"] = response["credentials"]["applicationId"]
        self.algolia_credentials["searchApiKey"] = response["credentials"]["searchApiKey"]
        return self.algolia_credentials

    def _get_object_id(self, ticker: str) -> str:
        """Gets the Trading212 object id for a ticker symbol.

        Args:
            ticker: Ticker symbol.

        Returns:
        """
        if self.object_id_to_ticker.get(ticker):
            return ticker

        if not self.ticker_to_object_id.get(ticker):
            data = self.get_equity_data(ticker)
            self.ticker_to_object_id[ticker] = data["objectID"]
            self.object_id_to_ticker[data["objectID"]] = ticker

        return self.ticker_to_object_id[ticker]

    @enforce_auth
    def get_equity_data(self, ticker: str) -> Dict:
        """Gets more Trading212 information about a ticker.

        Args:
            ticker: Ticker symbol

        Returns:
            Ticker data
        """
        page_number = 0
        # Payload was gotten from studying Trading212's requests.
        payload = {"requests": [
            {
                "indexName": "instrument.ld4.EN",
                "params": f"attributesToHighlight=%5B%22name%22%2C%22shortName%22%2C%22exchangeName%22%2C"
                          f"%22uiType%22%5D&attributesToRetrieve=%5B%22name%22%2C%22shortName%22%2C"
                          f"%22exchangeName%22%2C%22uiType%22%2C%22exchangeCountryCode%22%2C%22currencyCode%22%2C"
                          f"%22category%22%2C%22workingScheduleId%22%5D&filters=(category%3AEQUITY)%20AND"
                          f"%20(state.demo.enabled%3Atrue)%20AND%20(state.demo.conditionalVisibility%3Afalse)%20AND"
                          f"%20(NOT%20dealerExclusions%3AAVUSUK)&getRankingInfo=true&hitsPerPage=50&"
                          f"optionalFilters=%5B%5D&page={page_number}&query={ticker}&sumOrFiltersScores=true&"
                          f"tagFilters="
            }
        ]}

        credentials = self._get_algolia_credentials()
        url = ALGOLIA_SEARCH_URL.format(application_id=credentials["applicationId"],
                                        search_api_key=credentials["searchApiKey"])

        response = self.session.post(url, json=payload).json()
        matches = response.get("results")[0]["hits"]

        result = {}
        for match in matches:
            if match.get("category").upper() == "EQUITY" and match.get("uiType") == "STOCK" \
                    and match.get("shortName").upper() == ticker.upper() \
                    and match.get("exchangeName").upper() in SUPPORTED_EXCHANGES:
                result = match
                break

        return result

    @enforce_auth
    def get_ask_price(self, ticker: str) -> Dict:
        """Gets the most recent ask price for the ticker.

        Args:
            ticker: ticker symbol

        Returns:
            Asking price data
        """
        # The payload can take in multiple tickers like:
        # [{"ticker":"TSLA_US_EQ","useAskPrice":true},{"ticker":"PLTR_US_EQ","useAskPrice":true}]
        payload = [{"ticker":self._get_object_id(ticker), "useAskPrice":True}]
        response = self.session.put(TICKER_PRICE_URL, json=payload).json()
        if not isinstance(response, list):
            raise ValueError(f"The ticker {ticker} is invalid.")

        return response[0].get("response")


    @enforce_auth
    def get_status(self, order_id: Union[int, str]) -> Dict:
        """Gets the status of the placed order.

        Args:
            order_id: Order id.

        Returns:
            Data with information about order status
        """
        order_handler = ExistingOrdersHandler(self.session)
        existing_orders = order_handler.from_summary()

        for order in existing_orders:
            if order['orderId'] == str(order_id):
                return {"status": OrderStatus.SUBMITTED}

        for increment in range(FILLID_MAX_INCREMENT):
            fill_id = int(order_id) + increment
            response = self.session.get(f"{ORDER_HISTORY}/{fill_id}", json=[])
            if response.status_code == 200:
                break

        response = response.json()
        # TODO: Figure out what the difference between Rejected and Non existent order ids is.
        fill_details = response.get("sections", [])
        if not fill_details:
            return {"status": OrderStatus.REJECTED}

        fill_details = fill_details[2]
        is_executed = False
        fill_price = None
        fill_quantity = None
        exchange_rate = 1
        for data in fill_details.get("rows", []):
            description = data.get("description", {"key": None})
            details = data.get("value", {"context": None})
            if description["key"] == "history.details.order.fill.date-executed.key" and details["context"]:
                is_executed = True

            # TODO: Handle the case if the account is in USD
            if description["key"] == "history.details.order.exchange-rate.key" and details["context"]:
                exchange_rate = details["context"]["quantity"]

            if description["key"] == "history.details.order.fill.price.key" and details["context"]:
                fill_price = details["context"]["amount"]

            if description["key"] == "history.details.order.fill.quantity.key" and details["context"]:
                fill_quantity = details["context"]["quantity"]

        if fill_price is None:
            return {"status": OrderStatus.CANCELLED}

        fill_price /= exchange_rate

        if is_executed:
            if not fill_quantity:
                print(f"WARNING: Could not extract the fill quantity for order: {order_id}")

            fill_data = {
                "status": OrderStatus.COMPLETED,
                "price": fill_price,
                "quantity": fill_quantity
            }
            return fill_data
        else:
            return {"status": OrderStatus.REJECTED}

    @enforce_auth
    def get_account_details(self) -> Dict:
        """Get the value of assets in account."""
        response = self.session.post(ACCOUNT_SUMMARY_URL, json=[]).json()
        details = {
            "cash": response.get("cash").get("freeForStocks"),
            "total": response.get("cash").get("total")
        }

        return details

    def get_position(self, ticker: str) -> Optional[Dict]:
        """Get the position of ticker."""
        positions = self.get_positions({ticker})
        if positions:
            return positions[0]
        else:
            return None

    @enforce_auth
    def get_positions(self, tickers: Set[str]) -> List[Dict]:
        """Get position data from all tickers."""
        response = self.session.post(ACCOUNT_SUMMARY_URL, json=[]).json()
        SummarySchema.model_validate(response)
        positions = []

        for position in response.get("open", {}).get("items", []):
            ticker = position["code"].split("_", 1)[0]
            if ticker in tickers:
                Position.model_validate(position)
                positions.append(position)

        return positions

    # TODO: Create a function to make any call to any trading212 url for experts.
    # TODO: Add logging of results make to each api call.
    # TODO: Allow enforce auth take in a custom Driver.
    # TODO: Use LLMs to make model changes during schema changes.