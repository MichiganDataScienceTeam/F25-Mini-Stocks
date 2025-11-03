from typing import List, Tuple, Union, Callable, Optional
from dataclasses import dataclass
import math
import heapq

from core.types import (
    Order, OrderType, OrderRequest, Timestamp, Quantity, 
    Price, OrderId, OrderFactory, AgentId
)


@dataclass(frozen=True)
class MarketData:
    """
    Read-only market data snapshot

    Attributes:
        bids (Tuple[Order, ...]): A Tuple of copies of all resting bids
        asks (Tuple[Order, ...]): A Tuple of copies of all resting asks
    """

    bids: Tuple[Order, ...]
    asks: Tuple[Order, ...]


@dataclass(frozen=True)
class OrderAccepted:
    """Indicates that an order was accepted"""

    order_id: OrderId


@dataclass(frozen=True)
class OrderRejected:
    """Indicates that an order was rejected"""

    reason: str


OrderResult = Union[OrderAccepted, OrderRejected]


@dataclass(frozen=True)
class Trade:
    """Represents a single executed trade with all relevant details."""
    
    trade_id: int
    price: Price
    quantity: Quantity
    buyer_id: AgentId
    seller_id: AgentId
    timestamp: Timestamp


class MatchingEngine:
    """
    Manages the order book for a single instrument and matches trades.
    Uses price/time priority matching algorithm

    Attributes:
        bids (List[Order]): A list of buy orders, sorted by price/time
        asks (List[Order]): A list of sell orders, sorted by price/time
        trade_log (List[str]): A log of all trades that have occurred
    """

    def __init__(self, on_trade_callback: Optional[Callable[[Trade], None]] = None):
        """
        Initializes the MatchingEngine.

        Args:
            on_trade_callback: An optional function to call whenever a trade occurs.
        """
        
        self.bids: List[Tuple[Price, Timestamp, OrderId, Order]] = []
        self.asks: List[Tuple[Price, Timestamp, OrderId, Order]] = []
        self.trade_log: List[str] = []
        self._order_factory = OrderFactory()
        self._next_trade_id = 1
        self.on_trade_callback = on_trade_callback

    def get_market_data(self) -> MarketData:
        """
        Creates a read-only snapshot of the current market state.

        Args:
            None
        
        Returns:
            A MarketData object containing the data currently in this MatchingEngine
        """

        return MarketData(
            bids = tuple(sorted(
                [bid[-1] for bid in self.bids],
                key = lambda o: (-o.price, o.timestamp)
            )),
            asks = tuple(sorted(
                [ask[-1] for ask in self.asks],
                key = lambda o: (o.price, o.timestamp)
            ))
        )

    def prune_book(self, current_timestamp: Timestamp, max_age: int) -> None:
        """
        Removes stale orders from the book to maintain performance
        
        Args:
            current_timestamp: The current Timestamp
            max_age: The maximum number of ticks an order can remain in the book.
        
        Returns:
            None
        """

        self.bids = [o for o in self.bids if current_timestamp.value - o[-1].timestamp.value < max_age]
        self.asks = [o for o in self.asks if current_timestamp.value - o[-1].timestamp.value < max_age]

        heapq.heapify(self.bids)
        heapq.heapify(self.asks)

    def process_order(self, request: OrderRequest, timestamp: Timestamp) -> OrderResult:
        """
        Processes a new order request and returns a detailed result object

        Args:
            request: The OrderRequest object from the agent
            timestamp: The current Timestamp
        
        Returns:
            An OrderAccepted object on success, or an OrderRejected object on failure.
        """
        
        if request.quantity <= Quantity(0):
            return OrderRejected(f"Invalid quantity: {request.quantity}. Must be positive.")
        if not math.isfinite(request.price.value) or request.price.value < 0:
            return OrderRejected(f"Invalid price: {request.price}. Must be a non-negative finite number.")

        order = self._order_factory.create_order_from_request(request, timestamp)

        self._match_order(order)
            
        return OrderAccepted(order.order_id)

    def _match_order(self, incoming_order: Order) -> None:
        """
        (INTERNAL) Attempts to match an incoming order with existing orders in the order
        book, then updates the order book

        Args:
            incoming_order: The new Order to update the book with
        
        Returns:
            None
        """

        if incoming_order.order_type == OrderType.BUY:
            book_to_add = self.bids
            book_to_match = self.asks
        else: # SELL
            book_to_add = self.asks
            book_to_match = self.bids

        trades_made = []
        while incoming_order.quantity.value > 0 and len(book_to_match) > 0:
            resting_order_tuple = book_to_match[0]
            resting_order = resting_order_tuple[-1]

            can_match = (
                (incoming_order.order_type == OrderType.BUY and incoming_order.price >= resting_order.price) or
                (incoming_order.order_type == OrderType.SELL and incoming_order.price <= resting_order.price)
            )
            
            if not can_match:
                break

            heapq.heappop(book_to_match)

            trade_quantity = min(incoming_order.quantity, resting_order.quantity)
            trade_price = resting_order.price

            trade = self._create_trade_object(trade_quantity, trade_price, incoming_order, resting_order)
            trades_made.append(trade)

            incoming_order.quantity -= trade_quantity
            resting_order.quantity -= trade_quantity

            if resting_order.quantity.value > 0:
                heapq.heappush(book_to_match, resting_order_tuple)

        # Add remaining quantity to the book if any
        if incoming_order.quantity.value > 0:
            incoming_order_tuple = (
                incoming_order.price * (-1 if incoming_order.order_type == OrderType.BUY else 1),
                incoming_order.timestamp,
                incoming_order.order_id,
                incoming_order
            )

            heapq.heappush(book_to_add, incoming_order_tuple)
        
        for trade in trades_made:
            self._report_trade(trade)

    def _create_trade_object(self, quantity: Quantity, price: Price, incoming_order: Order, resting_order: Order) -> Trade:
        """(INTERNAL) Creates a structured Trade object from a match event."""

        now = incoming_order.timestamp
        
        buyer_id = incoming_order.agent_id if incoming_order.order_type == OrderType.BUY else resting_order.agent_id
        seller_id = incoming_order.agent_id if incoming_order.order_type == OrderType.SELL else resting_order.agent_id
        
        trade = Trade(
            trade_id=self._next_trade_id,
            price=price,
            quantity=quantity,
            buyer_id=buyer_id,
            seller_id=seller_id,
            timestamp=now
        )
        self._next_trade_id += 1

        return trade

    def _report_trade(self, trade: Trade) -> None:
        """
        (INTERNAL) Creates a structured Trade, reports it for settlement, and
        stores a descriptive log entry.
        
        Args:
            trade: The finalized Trade object to report.
        """
        
        if self.on_trade_callback:
            self.on_trade_callback(trade)

        log_entry = (
            f"[{trade.timestamp}] TRADE: {trade.quantity} units at ${trade.price:.2f} "
            f"(Buyer: {trade.buyer_id}, Seller: {trade.seller_id})"
        )
        
        self.trade_log.append(log_entry)

