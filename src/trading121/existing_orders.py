from typing import Union, Dict, List

import requests
from requests.models import Response

from .endpoints import AUTHENTICATE_URL, ACCOUNT_SUMMARY_URL
from .schemas.api_responses import SummarySchema, AfterOrderSchema


class ExistingOrdersHandler:
    """The ExistingOrdersHandler"""
    def __init__(self, session):
        self.session = session

    def from_summary(self, response: Union[Response, Dict, None] = None) -> List:
        """Extracts existing orders using the Trading212 summary response or endpoint.

        Args:
            response: If response is not provided, it accesses the endpoint directly to extract the response.

        Returns:
        """
        if not response:
            self.session.get(AUTHENTICATE_URL)
            response = self.session.post(ACCOUNT_SUMMARY_URL, json=[]).json()

        if isinstance(response, requests.models.Response):
            response = response.json()

        SummarySchema.model_validate(response)
        existing_orders = response.get("valueOrders", {}).get("items", [])
        return existing_orders

    def from_execution_response(self, response: Union[Response, Dict]) -> List:
        """Extracts existing orders using the response from placing an order.

        Args:
            response: The response of an order placed using `endpoints.DEMO_PLACE_ORDER_URL`.

        Returns:
        """
        if isinstance(response, requests.models.Response):
            response = response.json()

        AfterOrderSchema.model_validate(response)
        existing_orders = response.get("account", {}).get("equityValueOrders", [])
        return existing_orders