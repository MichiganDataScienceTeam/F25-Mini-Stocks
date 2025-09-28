from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from core.market import Trade, MarketData
from core.types import Price, Quantity, AgentId, OrderRequest, OrderType
from agents.base_agent import TradingAgent


# --- Configuration Constants ---
DEFAULT_INITIAL_CASH = Price(1_000_000.0)
DEFAULT_INITIAL_POSITION = Quantity(0)
DEFAULT_POSITION_LIMIT = Quantity(1000)
DEFAULT_MAX_ORDER_SIZE = Quantity(1000)


@dataclass
class AccountState:
    """Holds an agent's cash and position."""

    agent_id: AgentId
    cash: Price
    position: Quantity


class RiskViolationType(Enum):
    """Types of risk control violations"""

    INSUFFICIENT_CASH = "insufficient_cash"
    POSITION_LIMIT_EXCEEDED = "position_limit_exceeded"
    ORDER_SIZE_TOO_LARGE = "order_size_too_large"
    SELF_TRADE = "self_trade"


@dataclass
class RiskViolation:
    """Details about a risk control violation"""
    
    violation_type: RiskViolationType
    message: str
    attempted_order: OrderRequest


class Broker:
    """
    The 'broker' for the simulation. Manages TradingAgent accounts, validates orders
    against risk controls, and settles trades.
    """

    def __init__(self, agents: List[TradingAgent], 
                 initial_cash: Price = DEFAULT_INITIAL_CASH, 
                 initial_position: Quantity = DEFAULT_INITIAL_POSITION,
                 default_position_limit: Quantity = DEFAULT_POSITION_LIMIT,
                 default_max_order_size: Quantity = DEFAULT_MAX_ORDER_SIZE):
        """
        Initializes an account for each agent with starting cash and risk limits.

        Args:
            agents: A list of all TradingAgent instances participating.
            initial_cash: The amount of cash each agent starts with.
            initial_position: The number of shares each agent starts with.
            default_position_limit: Maximum long or short position allowed per agent.
            default_max_order_size: Maximum quantity allowed in a single order.
        """

        self.accounts: Dict[AgentId, AccountState] = {}
        self.position_limits: Dict[AgentId, Quantity] = {}
        self.max_order_sizes: Dict[AgentId, Quantity] = {}
        
        # Initialize accounts for each agent
        for agent in agents:
            self.accounts[agent.agent_id] = AccountState(
                agent_id=agent.agent_id,
                cash=initial_cash,
                position=initial_position
            )
            self.position_limits[agent.agent_id] = default_position_limit
            self.max_order_sizes[agent.agent_id] = default_max_order_size
        
    def get_account_state(self, agent_id: AgentId) -> AccountState | None:
        """
        Retrieves the current account state for a given agent.
        
        Args:
            agent_id: The AgentId to look up
            
        Returns:
            The AccountState for the TradingAgent or None if not found
        """

        return self.accounts.get(agent_id)
    
    def set_max_order_size(self, agent_id: AgentId, size: Quantity) -> None:
        """
        Set maximum order size for a specific agent.

        Args:
            agent_id: The AgentId to update the max order size of
            size: The max size
        """

        self.max_order_sizes[agent_id] = size

    def validate_order(self, request: OrderRequest, market_data: MarketData) -> RiskViolation | None:
        """
        Validates an order request against risk controls.
        
        Args:
            request: The OrderRequest to validate.
            market_data: The current state of the market.
            
        Returns:
            None if the order passes all risk checks, or a RiskViolation object
            describing the first violation encountered.
        """

        account = self.accounts.get(request.agent_id)
        if not account:
            return RiskViolation(
                RiskViolationType.INSUFFICIENT_CASH,
                f"No account found for agent {request.agent_id}",
                request
            )

        # Check maximum order size
        max_size = self.max_order_sizes.get(request.agent_id, DEFAULT_MAX_ORDER_SIZE)
        if request.quantity > max_size:
            return RiskViolation(
                RiskViolationType.ORDER_SIZE_TOO_LARGE,
                f"Order size {request.quantity} exceeds maximum {max_size}",
                request
            )

        # Self-trade prevention
        if request.order_type == OrderType.BUY and market_data.asks:
            best_ask = market_data.asks[0]
            if request.price >= best_ask.price and best_ask.agent_id == request.agent_id:
                return RiskViolation(
                    RiskViolationType.SELF_TRADE,
                    "Order would cross with own resting order.",
                    request
                )
        elif request.order_type == OrderType.SELL and market_data.bids:
            best_bid = market_data.bids[0]
            if request.price <= best_bid.price and best_bid.agent_id == request.agent_id:
                return RiskViolation(
                    RiskViolationType.SELF_TRADE,
                    "Order would cross with own resting order.",
                    request
                )

        # Position and cash validation logic
        position_limit = self.position_limits.get(request.agent_id, DEFAULT_POSITION_LIMIT)
        current_position = account.position
        
        if request.order_type == OrderType.BUY:
            potential_position = current_position + request.quantity
            if potential_position > position_limit:
                return RiskViolation(
                    RiskViolationType.POSITION_LIMIT_EXCEEDED,
                    f"Buy order would result in position {potential_position}, exceeding limit {position_limit}",
                    request
                )
            
            required_cash = request.price * request.quantity
            if account.cash < required_cash:
                return RiskViolation(
                    RiskViolationType.INSUFFICIENT_CASH,
                    f"Insufficient cash: need ${required_cash:.2f}, have ${account.cash:.2f}",
                    request
                )
                
        else:  # SELL order
            potential_position = current_position - request.quantity
            if potential_position < -position_limit:
                return RiskViolation(
                    RiskViolationType.POSITION_LIMIT_EXCEEDED,
                    f"Sell order would result in position {potential_position}, exceeding limit -{position_limit}",
                    request
                )

        return None

    def settle_trade(self, trade: Trade) -> None:
        """
        Updates agent accounts after a trade.
        """

        trade_value = trade.price * trade.quantity
        
        if trade.buyer_id in self.accounts:
            self.accounts[trade.buyer_id].cash -= trade_value
            self.accounts[trade.buyer_id].position = self.accounts[trade.buyer_id].position + trade.quantity
        
        if trade.seller_id in self.accounts:
            self.accounts[trade.seller_id].cash += trade_value
            self.accounts[trade.seller_id].position = self.accounts[trade.seller_id].position - trade.quantity

