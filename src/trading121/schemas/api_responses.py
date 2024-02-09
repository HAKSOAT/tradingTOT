from typing import Optional, Union
from typing import List, Dict
from pydantic import BaseModel

from trading121.constants import VALUE_UNAVAILABLE


class Position(BaseModel):
    positionId: str
    humanId: str
    created: str
    averagePrice: float
    averagePriceConverted: float
    currentPrice: float
    value: float
    investment: float
    code: str
    margin: float
    ppl: float
    quantity: float
    maxBuy: Optional[float] = VALUE_UNAVAILABLE
    maxSell: Optional[float] = VALUE_UNAVAILABLE
    maxOpenBuy: Optional[float] = VALUE_UNAVAILABLE
    maxOpenSell: Optional[float] = VALUE_UNAVAILABLE
    frontend: str
    autoInvestQuantity: float
    fxPpl: float


class Open(BaseModel):
    unfilteredCount: int
    items: List[Position]


class Cash(BaseModel):
    free: float
    total: float
    interest: float
    indicator: float
    commission: float
    cash: float
    ppl: float
    result: float
    spreadBack: float
    nonRefundable: float
    dividend: float
    stockInvestment: float
    freeForStocks: float
    totalCashForWithdraw: float
    blockedForStocks: float
    pieCash: int


class Orders(BaseModel):
    unfilteredCount: int
    items: List[Dict[str, str]]


class ValueOrders(BaseModel):
    unfilteredCount: int
    items: List[Dict[str, Union[str, int]]]


class SummarySchema(BaseModel):
    cash: Cash
    open: Open
    orders: Orders
    valueOrders: ValueOrders


class EquityValueOrder(BaseModel):
    orderId: str
    type: str
    code: str
    value: int
    filledValue: int
    status: str
    currencyCode: str
    created: str
    frontend: str


class Account(BaseModel):
    dealer: str
    positions: List[Position]
    cash: Cash
    limitStop: List[Dict[str, str]]
    oco: List[Dict[str, str]]
    ifThen: List[Dict[str, str]]
    equityOrders: List[Dict[str, str]]
    equityValueOrders: List[EquityValueOrder]
    id: int
    timestamp: int

class AfterOrderSchema(BaseModel):
    account: Account
