from __future__ import annotations

import math
import random
from typing import List

from collections import deque

from core.types import OrderRequest, OrderType, Price, Quantity, AgentId
from core.market import MarketData
from core.broker import AccountState
from agents.base_agent import TradingAgent

from config import *


class BadMarketMaker(TradingAgent):
    """
    Not a very good market maker
    """

    def __init__(self, agent_id: AgentId, half_spread: Price = Price(2),
                 default_fair_value: Price = Price(100)):
        super().__init__(agent_id)
        self.is_house_agent = True
        self.half_spread = half_spread
        self.default_fair_value = default_fair_value

    def propose_trades(self, market_data: MarketData, my_account_state: AccountState) -> List[OrderRequest]:
        """
        Estimate fair value and make a market with that estimate
        """

        best_bid = market_data.bids[0].price if market_data.bids else None
        best_ask = market_data.asks[0].price if market_data.asks else None

        if best_bid and best_ask:
            FAIR_VALUE = (best_bid + best_ask) / 2
        else:
            FAIR_VALUE = self.default_fair_value + Price(random.randint(-10, 10)/5)

        return [OrderRequest(self.agent_id, OrderType.BUY, FAIR_VALUE - self.half_spread, Quantity(1)),
                OrderRequest(self.agent_id, OrderType.SELL, FAIR_VALUE + self.half_spread, Quantity(1))]


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
                price = market_data.asks[0].price + Price(random.random())
                quantity = min(HOUSE_POSITION_LIMIT - max_position, market_data.asks[0].quantity)
                quantity = min(quantity, DEFAULT_MAX_ORDER_SIZE)
                if quantity == Quantity(0):
                    return []
                return [OrderRequest(self.agent_id, OrderType.BUY, price, quantity)]
            else:
                price = market_data.bids[0].price - Price(random.random())
                quantity = min(HOUSE_POSITION_LIMIT + min_position, market_data.bids[0].quantity)
                quantity = min(quantity, DEFAULT_MAX_ORDER_SIZE)
                if quantity == Quantity(0):
                    return []
                return [OrderRequest(self.agent_id, OrderType.SELL, price, quantity)]
        
        return []


class RandomReverter(TradingAgent):
    """
    Enforces reversion property at a loss
    """

    def __init__(self, agent_id: AgentId, default_fair_value: Price = Price(100), diff_coef: float = 0.1):
        super().__init__(agent_id)
        self.is_house_agent = True
        self.fair_value = default_fair_value
        self.diff_coef = diff_coef
    
    def propose_trades(self, market_data, my_account_state):
        """
        Place orders pushing the market towards "fair value" with
        probabilities increasing with deviations
        """

        # Don't trade when insufficient orders
        if (not market_data.bids) or (not market_data.asks):
            return []
        
        mid_price = (market_data.bids[0].price + market_data.asks[0].price) / 2

        diff = mid_price - self.fair_value
        diff = diff if diff > Price(0) else -diff

        direction = OrderType.BUY if mid_price < self.fair_value else OrderType.SELL

        orders = []

        if random.random() < (1 - 2**(-self.diff_coef * diff.value)):
            orders.append(OrderRequest(
                self.agent_id,
                direction,
                self.fair_value,
                Quantity(random.randint(1, DEFAULT_MAX_ORDER_SIZE.value))
            ))

            if direction == OrderType.BUY:
                orders.append(OrderRequest(
                    self.agent_id,
                    direction,
                    market_data.asks[0].price,
                    Quantity(random.randint(1, DEFAULT_MAX_ORDER_SIZE.value))
                ))
            else: # SELL
                orders.append(OrderRequest(
                    self.agent_id,
                    direction,
                    market_data.bids[0].price,
                    Quantity(random.randint(1, DEFAULT_MAX_ORDER_SIZE.value))
                ))

        return orders

class MysteryBot(TradingAgent):
    """
    Mysterious bot
    """

    def __init__(self, agent_id, default_fair_value = Price(100),
                 reverting_config = (4, 1.5, 0.25),
                 momentum_config = (4, 2.5, 0.67),
                 levels = [0.2 * i for i in range(1, 10)],
                 up_bias = 0.1):
        
        super().__init__(agent_id)
        self.is_house_agent = True

        self.default_fair_value = default_fair_value
        self.up_bias = up_bias

        self.state = "REVERTING"
        self.max_switch_cooldown = 500
        self.switch_cooldown = self.max_switch_cooldown

        self.reverting_config = reverting_config
        self.momentum_config = momentum_config

        self.levels = levels

        self.mid_history = deque(maxlen = 10)

    def _maybe_switch_state(self):
        self.switch_cooldown = max(0, self.switch_cooldown - 1)

        if self.switch_cooldown == 0:
            self.switch_cooldown = self.max_switch_cooldown + random.randint(0, 100)
            self.state = "MOMENTUM" if self.state == "REVERTING" else "REVERTING"

    def compute_average_price(self, mid_price: Price) -> Price:
        """
        Assumes there are bids and asks
        """
        
        self.mid_history.append(mid_price)

        return sum(self.mid_history) / len(self.mid_history)

    def _depth_profile(self):
        """
        Hmmmmmmm
        """
        
        config = self.reverting_config if self.state == "REVERTING" else self.momentum_config

        quantities = []
        for x in self.levels:
            c, k, s = config
            temp = c * math.pow(x, k - 1) * math.exp(-x / s)
            temp2 = max(1, int(round(temp * DEFAULT_MAX_ORDER_SIZE.value)))
            
            quantities.append(Quantity(temp2))
        
        return quantities

    def propose_trades(self, market_data, my_account_state) -> List["OrderRequest"]:
        """
        Hmmmmmm
        """

        best_bid = market_data.bids[0].price if market_data.bids else None
        best_ask = market_data.asks[0].price if market_data.asks else None

        if best_bid and best_ask:
            mid_price = (best_bid + best_ask) / 2
        else:
            mid_price = self.default_fair_value
        
        average_price = self.compute_average_price(mid_price)
        self._maybe_switch_state()

        if self.state == "MOMENTUM":
            direction = 1 if (mid_price > average_price or random.random() < self.up_bias or mid_price < Price(30)) else -1
        else:
            direction = 0

        mid_price += Price(direction * 0.2)

        orders = []
        depths = self._depth_profile()

        for i, quantity in enumerate(depths):
            bid_price = mid_price - Price(self.levels[i])
            ask_price = mid_price + Price(self.levels[i])

            orders.append(OrderRequest(self.agent_id, OrderType.BUY, bid_price, quantity))
            orders.append(OrderRequest(self.agent_id, OrderType.SELL, ask_price, quantity))

        return orders

