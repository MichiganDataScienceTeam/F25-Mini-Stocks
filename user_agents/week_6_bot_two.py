from __future__ import annotations

import random
from typing import List, Tuple, TYPE_CHECKING

from core.types import OrderRequest, OrderType, Price, Quantity, AgentId
from core.market import MarketData
from agents.base_agent import TradingAgent
from config import *

if TYPE_CHECKING:
    from core.broker import AccountState

# class BabyBot(TradingAgent):
#     """
#     An agent that simulates sma
#     """

#     def __init__(self, agent_id: AgentId, default_fair_value: Price, window: int = 10, spread: Price = Price(1)):
#         super().__init__(agent_id)
#         self.default_fair_value = default_fair_value
#         self.spread = spread
#         self.window = window
#         self.position_limit = DEFAULT_POSITION_LIMIT
#         self.base_amount = DEFAULT_MAX_ORDER_SIZE
#         self.past_prices = []

#     def propose_trades(self, market_data: MarketData, acc_state: "AccountState") -> List[OrderRequest]:
#         """
#         Estimate fair value and make a market with that estimate
#         """

#         trades = []

#         best_bid = market_data.bids[0].price if market_data.bids else None
#         best_ask = market_data.asks[0].price if market_data.asks else None

#         if best_bid and best_ask:
#             FAIR_VALUE = (best_bid + best_ask) / 2
#         else:
#             FAIR_VALUE = self.default_fair_value
        
#         self.past_prices.append(FAIR_VALUE)
#         if len(self.past_prices) > 10:
#             self.past_prices.pop(0)
        
#         sma = sum(self.past_prices) / len(self.past_prices)

#         # at order limit
#         if acc_state.position.value >= self.position_limit.value // 2:
#             if best_bid:
#                 half_amount = min(acc_state.position.value // 2, self.base_amount.value // 2)
#                 trades.append(OrderRequest(self.agent_id, OrderType.SELL, best_bid, Quantity(half_amount)))
#                 trades.append(OrderRequest(self.agent_id, OrderType.SELL, sma, Quantity(half_amount)))
#             else:
#                 trades.append(OrderRequest(self.agent_id, OrderType.SELL, sma, min(acc_state.position, self.base_amount)))
#         elif acc_state.position.value <= -self.position_limit.value // 2:
#             if best_ask:
#                 half_amount = min(-acc_state.position.value // 2, self.base_amount.value // 2)
#                 trades.append(OrderRequest(self.agent_id, OrderType.BUY, best_ask, Quantity(half_amount)))
#                 trades.append(OrderRequest(self.agent_id, OrderType.BUY, sma, Quantity(half_amount)))
#             else:
#                 trades.append(OrderRequest(self.agent_id, OrderType.BUY, sma, min(-acc_state.position, self.base_amount)))
#         else:
#             # propose trades
#             trades.append(OrderRequest(self.agent_id, OrderType.BUY, sma - self.spread, self.base_amount))
#             trades.append(OrderRequest(self.agent_id, OrderType.SELL, sma + self.spread, self.base_amount))

#         return trades


class ToddlerBot(TradingAgent):
    """
    A market making agent
    """

    def __init__(self, agent_id: AgentId, default_fair_value: Price = Price(100), window: int = 10):
        super().__init__(agent_id)
        self.default_fair_value = default_fair_value
        self.window = window
        self.past_prices = []

    def propose_trades(self, market_data: MarketData, acc_state: "AccountState") -> List[OrderRequest]:
        """
        Estimate fair value and make a market with that estimate
        """

        sma = self.compute_fair_price(market_data) # Moving average of 10 most recent ticks
        spread = self.compute_fair_spread(market_data, sma) 
        
        # compute bias ratio: -1 (strongly short), +1 (strongly long)
        position_ratio = acc_state.position.value / DEFAULT_POSITION_LIMIT.value
        buy_bias = max(0, 1.0 - position_ratio)
        sell_bias = max(0, 1.0 + position_ratio)
        buy_qty = min(Quantity(int(DEFAULT_MAX_ORDER_SIZE.value * buy_bias)), DEFAULT_MAX_ORDER_SIZE)
        sell_qty = min(Quantity(int(DEFAULT_MAX_ORDER_SIZE.value * sell_bias)), DEFAULT_MAX_ORDER_SIZE)
        
        # propose trades
        trades = []
        trades.append(OrderRequest(self.agent_id, OrderType.BUY, sma - spread, buy_qty))
        trades.append(OrderRequest(self.agent_id, OrderType.SELL, sma + spread, sell_qty))

        return trades
    
    def compute_fair_price(self, market_data: MarketData) -> Price:
        best_bid = market_data.bids[0].price if market_data.bids else None
        best_ask = market_data.asks[0].price if market_data.asks else None

        if best_bid and best_ask:
            FAIR_VALUE = (best_bid + best_ask) / 2
        else:
            FAIR_VALUE = self.default_fair_value
        
        self.past_prices.append(FAIR_VALUE)
        if len(self.past_prices) > 10:
            self.past_prices.pop(0)
        
        sma = sum(self.past_prices) / len(self.past_prices)
        
        return sma
    
    def compute_fair_spread(self, market_data: MarketData, mid_price: Price) -> Price:
        spread = Price(1)

        if market_data.bids and market_data.asks:
            half_spread = max(market_data.asks[0].price - mid_price, mid_price - market_data.bids[0].price)
            if half_spread.value > 0:
                spread = half_spread

        return spread

