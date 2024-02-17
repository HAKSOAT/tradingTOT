# TradingTOT

## Introduction
TradingTOT provides a Python-based solution for automating trading activities on Trading212. 
It leverages Selenium for web scraping and automation to interact with the trading platform, offering functionalities such as login automation and trade execution. 
While traders can use the Trading212 platform through the browser, this tool makes it possible to execute trades programmatically.

## Setup and Dependencies
### Prerequisites
- An installed web browser. Only Chrome, Microsoft Edge and Safari are supported.
- Python
- [Poetry](https://python-poetry.org/docs/)

### Installation
1. Clone the repository to your local machine: `git clone https://github.com/HAKSOAT/tradingTOT.git`
2. Install the required dependencies:
   ```sh
   cd tradingTOT
   poetry install
   ```

## Using the Project
To use this project, you need to configure your trading account credentials and set up environment variables for browser automation. 

You need to set the following environment variables:
- TRADINGTOT_EMAIL
- TRADINGTOT_PASSWORD
- TRADINGTOT_ENVIRONMENT

TRADINGTOT_ENVIRONMENT can be `live` or `demo`.

### Example Usage

```python
from tradingTOT import tradingTOT
from tradingTOT.enums import OrderType

tot = tradingTOT()
ticker = "MSFT"
equity_value_usd = 50

tot.get_account_details() # The first operation takes time if log in has never happened on this machine, or the existing token has expired.
# {'cash': 50.0, 'total': 56.05}

tot.get_equity_data(ticker) # Get information about an equity
# {
#    'category': 'EQUITY',
#    'shortName': 'MSFT',
#    'name': 'Microsoft',
#    'currencyCode': 'USD',
#    'workingScheduleId': 71,
#    'exchangeCountryCode': 'US',
#    'uiType': 'STOCK',
#    ...
# }
tot.get_ask_price(ticker) # Get the ask price for an equity
# {'timestamp': 1708093800000, 'price': 406.56, 'period': 'd1'}

tot.get_costs() # Getting the cost of placing an order.
# {'orderQuantity': 0.1557,
#  'sharesValue': 49.93,
#  'total': 50.0,
#  'exchangeRate': {'fromCurrency': 'USD', 'toCurrency': 'GBP', 'rate': 0.79348},
#  'costs': {'CURRENCY_CONVERSION_FEE': 0.07}}

response = tot.place_order(OrderType.BUY, ticker, equity_value_usd) # Place a buy order. Use OrderType.SELL for selling.
tot.get_status(response["orderId"]) # Get status of placed order.
# {'status': <OrderStatus.SUBMITTED: 'SUBMITTED'>}

tot.cancel_order(response["orderId"])
```


## Finding the Browser

The package will handle the finding the path of the web browser provided you have Chrome, Microsoft Edge or Safari installed. 
However, sometimes this may fail with a `FileNotFoundError`. 

In such cases, you can set the environment variable `BINARY_PATH`. To do this, you need to know what the binary path is.

For example, the binary path may be the following:

On Windows: `C:\Program Files\Google\Chrome\Application\chrome.exe`

On Linux: `/usr/bin/google-chrome`

On MacOS: `/Applications/Google Chrome.app`

You do not have to worry about the webdriver as Selenium 4 handles driver downloads itself.


## Disclaimer
This project is not officially affiliated with Trading212 or any other trading platform. It is developed as an independent tool to assist users in automating their trading strategies. Use at your own risk and discretion.