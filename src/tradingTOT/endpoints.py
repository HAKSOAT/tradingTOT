import os

from .enums import Environment
from .exceptions import EnvVarError


try:
    environment = os.environ.get("TRADINGTOT_ENVIRONMENT", "")
    environment = getattr(Environment, environment)
except AttributeError:
    raise EnvVarError(f"Set a valid environment variable for `TRADINGTOT_ENVIRONMENT`. "
                      f"Supported values are {', '.join(Environment.__members__)}.")


HOME_URL = "https://www.trading212.com/"
VALIDATE_URL = f"https://{environment}.trading212.com/rest/v1/equity/value-order/validate"
PLACE_ORDER_URL = f"https://{environment}.trading212.com/rest/v1/equity/value-order"
ORDER_COSTS_URL = f"https://{environment}.trading212.com/rest/v1/equity/value-order/review"
TICKER_PRICE_URL = f"https://{environment}.trading212.com/charting/v1/watchlist/batch/deviations"
TICKER_PRICE_URL_V2 = f"https://{environment}.services.trading212.com/charting/v2/json/{{object_id}}/preview/extended/deviation"
AUTHENTICATE_URL = f"https://{environment}.trading212.com/rest/v1/webclient/authenticate"
ORDER_HISTORY = f"https://{environment}.trading212.com/rest/history/orders"
ACCOUNT_SUMMARY_URL = f"https://{environment}.trading212.com/rest/trading/v1/accounts/summary"
ACCOUNT_SUMMARY_URL_SERVICES = f"https://{environment}.services.trading212.com/rest/trading/v1/accounts/summary"
ALGOLIA_CONFIG_URL = f"https://{environment}.trading212.com/rest/algolia/v1/search/config/EN"
ALGOLIA_SEARCH_URL = "https://{application_id}-dsn.algolia.net/1/indexes/*/queries?" \
                          "x-algolia-api-key={search_api_key}&x-algolia-application-id={application_id}"