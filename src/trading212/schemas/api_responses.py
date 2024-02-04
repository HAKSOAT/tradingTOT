from typing import List, Dict, Optional, Union
from pydantic import BaseModel, ValidationError
from typing import List, Dict
from pydantic import BaseModel


class Item(BaseModel):
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
    maxBuy: Optional[float]
    maxSell: Optional[float]
    maxOpenBuy: Optional[float]
    maxOpenSell: Optional[float]
    frontend: str
    autoInvestQuantity: float
    fxPpl: float


class Open(BaseModel):
    unfilteredCount: int
    items: List[Item]


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
    maxBuy: Optional[float]
    maxSell: Optional[float]
    maxOpenBuy: Optional[float]
    maxOpenSell: Optional[float]
    frontend: str
    autoInvestQuantity: float
    fxPpl: float

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
