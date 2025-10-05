from __future__ import annotations

import random
from typing import List, TYPE_CHECKING

from core.types import OrderRequest, OrderType, Price, Quantity, AgentId
from core.market import MarketData
from agents.base_agent import TradingAgent

if TYPE_CHECKING:
    from core.broker import AccountState


class BadMarketMaker(TradingAgent):
    """
    Not a very good market maker
    """

    def __init__(self, agent_id: AgentId, default_fair_value: Price):
        super().__init__(agent_id)
        self.default_fair_value = default_fair_value

    def propose_trades(self, market_data: MarketData, my_account_state: "AccountState") -> List[OrderRequest]:
        """
        Estimate fair value and make a market with that estimate
        """

        best_bid = market_data.bids[0].price if market_data.bids else None
        best_ask = market_data.asks[0].price if market_data.asks else None

        FAIR_VALUE = self.default_fair_value + Price(random.randint(-10, 10)/5)

        if best_bid and best_ask:
            FAIR_VALUE = (best_bid + best_ask) / 2
        
        HALF_SPREAD = Price(2)

        return [OrderRequest(self.agent_id, OrderType.BUY, FAIR_VALUE - HALF_SPREAD, Quantity(1)),
                OrderRequest(self.agent_id, OrderType.SELL, FAIR_VALUE + HALF_SPREAD, Quantity(1))]


class NoiseTraderBot(TradingAgent):
    """
    An agent that simulates random, uninformed "retail" trading.
    """

    def __init__(self, agent_id: AgentId, trade_probability: float = 0.3, max_trade_size: int = 50):
        super().__init__(agent_id)
        self.trade_probability = trade_probability
        self.max_trade_size = max_trade_size

    def propose_trades(self, market_data: MarketData, my_account_state: "AccountState") -> List[OrderRequest]:
        """On a random chance, submits an aggressive order to simulate a market trade."""
        if random.random() < self.trade_probability:
            # Determine what orders are actually possible
            can_buy = len(market_data.asks) > 0
            can_sell = len(market_data.bids) > 0
            
            # If only one direction is possible, do that
            if can_buy and not can_sell:
                order_type = OrderType.BUY
            elif can_sell and not can_buy:
                order_type = OrderType.SELL
            elif can_buy and can_sell:
                # Both are possible, choose randomly
                order_type = random.choice([OrderType.BUY, OrderType.SELL])
            else:
                # Neither is possible
                return []
            
            if order_type == OrderType.BUY:
                price = market_data.asks[0].price
                quantity = Quantity(random.randint(1, max(1, min(self.max_trade_size, market_data.asks[0].quantity.value))))
                return [OrderRequest(self.agent_id, OrderType.BUY, price, quantity)]
            else:
                price = market_data.bids[0].price
                quantity = Quantity(random.randint(1, max(1, min(self.max_trade_size, market_data.bids[0].quantity.value))))
                return [OrderRequest(self.agent_id, OrderType.SELL, price, quantity)]
        
        return []

