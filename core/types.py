from dataclasses import dataclass
from enum import Enum
from typing import Self


@dataclass(init=True, repr=False, eq=False, order=False, frozen=True)
class _NumericValue:
    """
    An internal base class for creating typesafe numeric value objects.
    """

    value: int | float

    def __eq__(self, other):
        if isinstance(other, self.__class__): return self.value == other.value
        if isinstance(other, (int, float)): return self.value == other
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        return not result if result is not NotImplemented else NotImplemented

    def __lt__(self, other):
        if isinstance(other, self.__class__): return self.value < other.value
        if isinstance(other, (int, float)): return self.value < other
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, self.__class__): return self.value <= other.value
        if isinstance(other, (int, float)): return self.value <= other
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, self.__class__): return self.value > other.value
        if isinstance(other, (int, float)): return self.value > other
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, self.__class__): return self.value >= other.value
        if isinstance(other, (int, float)): return self.value >= other
        return NotImplemented

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value})"
    
    def __format__(self, format_spec=""):
        return self.value.__format__(format_spec)

    def _unsupported_op(self, op_name):
        raise TypeError(
            f"Unsupported operation: '{op_name}'. "
            f"{self.__class__.__name__} objects do not support this arithmetic. "
            "If you need the raw value, use '.value'."
        )

    def __mul__(self, other) -> Self | None : self._unsupported_op("*")
    
    def __rmul__(self, other) -> Self | None : self._unsupported_op("*")
    
    def __truediv__(self, other) -> Self | None : self._unsupported_op("/")
    
    def __rtruediv__(self, other) -> Self | None : self._unsupported_op("/")
    
    def __add__(self, other) -> Self | None : self._unsupported_op("+")
    
    def __sub__(self, other) -> Self | None : self._unsupported_op("-")


@dataclass(init=True, repr=False, eq=False, order=False, frozen=True)
class OrderId(_NumericValue):
    """(int) Unique ID for an Order"""

    value: int

    def __post_init__(self):
        if not isinstance(self.value, int): raise TypeError("OrderId must be an integer.")


@dataclass(init=True, repr=False, eq=False, order=False, frozen=True)
class AgentId(_NumericValue):
    """(int) Unique ID for an Agent"""

    value: int

    def __post_init__(self):
        if not isinstance(self.value, int): raise TypeError("AgentId must be an integer.")


@dataclass(init=True, repr=False, eq=False, order=False, frozen=True)
class Price(_NumericValue):
    """(float) Price for an Order"""

    value: float

    def __post_init__(self):
        if not isinstance(self.value, (int, float)): raise TypeError("Price must be a number.")
    
    def __add__(self, other):
        if isinstance(other, Price): return Price(self.value + other.value)
        self._unsupported_op("+")

    def __sub__(self, other):
        if isinstance(other, Price): return Price(self.value - other.value)
        self._unsupported_op("-")

    def __mul__(self, other):
        if isinstance(other, Quantity):
            return Price(self.value * other.value)
        elif isinstance(other, (int, float)):
            return Price(self.value * other)
        
        self._unsupported_op("*")
    
    def __truediv__(self, other):
        if isinstance(other, Quantity): return Price(self.value / other.value)
        elif isinstance(other, (int, float)): return Price(self.value / other)
        self._unsupported_op("/")

    def __neg__(self): return Price(-self.value)


@dataclass(init=True, repr=False, eq=False, order=False, frozen=True)
class Quantity(_NumericValue):
    """(int) Number of shares for an Order"""

    value: int

    def __post_init__(self):
        if not isinstance(self.value, int): raise TypeError("Quantity must be an integer.")
    
    def __add__(self, other):
        if isinstance(other, Quantity): return Quantity(self.value + other.value)
        self._unsupported_op("+")

    def __sub__(self, other):
        if isinstance(other, Quantity): return Quantity(self.value - other.value)
        self._unsupported_op("-")

    def __mul__(self, other):
        if isinstance(other, Price):
            return other * self
        elif isinstance(other, int):
            return Quantity(self.value * other)
        self._unsupported_op("*")

    def __neg__(self):
        return Quantity(-self.value)


class OrderType(Enum):
    """(Enum) BUY or SELL"""

    BUY = 1
    SELL = -1


@dataclass(init=True, repr=False, eq=False, order=False, frozen=True)
class OrderRequest:
    """
    A single order request created by an Agent

    Attributes:
        agent_id (AgentId): Unique ID for the Agent who submitted this Order
        order_type (OrderType): Whether the Order is a BUY or SELL
        price (Price): Price for this Order
        quantity (Quantity): The number of shares for this Order
    """

    agent_id: AgentId
    order_type: OrderType
    price: Price
    quantity: Quantity


@dataclass(init=True, repr=False, eq=False, order=False, frozen=True)
class Timestamp(_NumericValue):
    """(int) A discrete time tick from the simulation's virtual clock"""

    value: int

    def __post_init__(self):
        if not isinstance(self.value, int):
            raise TypeError("Timestamp must be an integer.")
        if self.value < 0:
            raise ValueError("Timestamp cannot be negative.")


@dataclass # Mutable for more performant partial filling
class Order:
    """
    A single order for use by the internal engine.

    Attributes:
        order_id (OrderId): Unique ID for this Order
        agent_id (AgentId): Unique ID for the Agent who submitted this Order
        order_type (OrderType): Whether the Order is a BUY or SELL
        price (Price): Price for this Order
        quantity (Quantity): The number of shares for this Order
        timestamp (Timestamp): Order received timestamp (set by the engine)
    """

    order_id: OrderId
    agent_id: AgentId
    order_type: OrderType
    price: Price
    quantity: Quantity
    timestamp: Timestamp


class OrderFactory:
    def __init__(self, start_id: int = 1):
        self._next_id = start_id

    def create_order_from_request(self, request: OrderRequest, timestamp: Timestamp) -> Order:
        """
        Creates a valid Order from an OrderRequest and timestamp

        Args:
            request: The OrderRequest submitted by the agent
            timestamp: The Timestamp the Order should be processed at
        """
        
        order_id = OrderId(self._next_id)
        self._next_id += 1
        
        return Order(
            order_id=order_id,
            agent_id=request.agent_id,
            order_type=request.order_type,
            price=request.price,
            quantity=request.quantity,
            timestamp=timestamp
        )

