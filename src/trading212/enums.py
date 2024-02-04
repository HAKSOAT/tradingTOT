from enum import Enum


class OrderStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"


class OrderType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Environment(str, Enum):
    demo = "demo"
    live = "live"