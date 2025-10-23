from __future__ import annotations

import random
from typing import List

from core.types import OrderRequest, OrderType, Price, Quantity, AgentId
from core.market import MarketData
from core.broker import AccountState
from agents.base_agent import TradingAgent

from config import *


class BadMarketMaker(TradingAgent):
    """
    Not a very good market maker
    """

    def __init__(self, agent_id: AgentId, default_fair_value: Price):
        super().__init__(agent_id)
        self.is_house_agent = True
        self.default_fair_value = default_fair_value

    def propose_trades(self, market_data: MarketData, my_account_state: AccountState) -> List[OrderRequest]:
        """
        Estimate fair value and make a market with that estimate
        """

        HALF_SPREAD = Price(2)

        best_bid = market_data.bids[0].price if market_data.bids else None
        best_ask = market_data.asks[0].price if market_data.asks else None

        if best_bid and best_ask:
            FAIR_VALUE = (best_bid + best_ask) / 2
        else:
            FAIR_VALUE = self.default_fair_value + Price(random.randint(-10, 10)/5)

        return [OrderRequest(self.agent_id, OrderType.BUY, FAIR_VALUE - HALF_SPREAD, Quantity(1)),
                OrderRequest(self.agent_id, OrderType.SELL, FAIR_VALUE + HALF_SPREAD, Quantity(1))]


class NoiseTraderBot(TradingAgent):
    """
    An agent that simulates random, uninformed "retail" trading.
    """

    def __init__(self, agent_id: AgentId, trade_probability: float = 0.3, max_order_size: Quantity = DEFAULT_MAX_ORDER_SIZE,
                 max_trade_size = None): # max_trade_size exists only for backwards compatibility
        super().__init__(agent_id)
        self.is_house_agent = True
        self.trade_probability = trade_probability
        self.max_order_size = max_order_size

    def propose_trades(self, market_data: MarketData, my_account_state: AccountState) -> List[OrderRequest]:
        """
        On a random chance, submits an aggressive order to simulate a market trade.
        """

        # Compute min and max positions
        max_position = my_account_state.position + sum([
            bid.quantity
            for bid in market_data.bids if bid.agent_id == self.agent_id
        ], start = Quantity(0))
        min_position = my_account_state.position - sum([
            ask.quantity
            for ask in market_data.asks if ask.agent_id == self.agent_id
        ], start = Quantity(0))

        if random.random() < self.trade_probability:
            # Determine what orders are actually possible
            can_buy = len(market_data.asks) > 0
            can_sell = len(market_data.bids) > 0
            
            # If only one direction is possible, do that
            if can_buy and not can_sell:
                order_type = OrderType.BUY
            elif can_sell and not can_buy:
                order_type = OrderType.SELL
            
            # Both are possible, choose randomly
            elif can_buy and can_sell:
                order_type = random.choice([OrderType.BUY, OrderType.SELL])
            
            # Neither is possible
            else:
                return []

            if order_type == OrderType.BUY:
                price = market_data.asks[0].price
                quantity = min(DEFAULT_POSITION_LIMIT - max_position, market_data.asks[0].quantity)
                if quantity == Quantity(0):
                    return []
                return [OrderRequest(self.agent_id, OrderType.BUY, price, quantity)]
            else:
                price = market_data.bids[0].price
                quantity = min(DEFAULT_POSITION_LIMIT + min_position, market_data.bids[0].quantity)
                if quantity == Quantity(0):
                    return []
                return [OrderRequest(self.agent_id, OrderType.SELL, price, quantity)]
        
        return []

