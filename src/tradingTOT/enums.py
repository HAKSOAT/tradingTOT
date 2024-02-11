from enum import Enum


class OrderStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class OrderType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Environment(str, Enum):
    demo = "demo"
    live = "live"


class FailureTypes(str, Enum):
    InsufficientValueForStocksSell = "InsufficientValueForStocksSell"
    ValuePrecisionMismatch = "ValuePrecisionMismatch"
