from __future__ import annotations

import random
from typing import List, TYPE_CHECKING

from core.types import OrderRequest, OrderType, Price, Quantity, AgentId
from core.market import MarketData
from agents.base_agent import TradingAgent

if TYPE_CHECKING:
    from core.broker import AccountState

from config import DEFAULT_MAX_ORDER_SIZE


class SimpleMarketMaker(TradingAgent):
    """
    Hopefully a better market maker
    """

    def __init__(self, agent_id: AgentId, default_fair_value: Price = Price(100)):
        super().__init__(agent_id)
        self.default_fair_value = default_fair_value

    def propose_trades(self, market_data: MarketData, my_account_state: "AccountState") -> List[OrderRequest]:
        """
        Estimate fair value and make a market with that estimate
        """

        best_bid = market_data.bids[0].price if market_data.bids else None
        best_ask = market_data.asks[0].price if market_data.asks else None

        FAIR_VALUE = self.default_fair_value

        if best_bid and best_ask:
            FAIR_VALUE = (best_bid + best_ask) / 2
        
        # if best_bid:
        #     half_spread_bid = best_bid + FAIR_VALUE
        #     half_spread_bid = half_spread_bid / 2 # ~FV +- 5
        # else:
        #     half_spread_bid = Price(2) #keeping some of original
        
        # if best_ask:
        #     half_spread_ask = best_ask + FAIR_VALUE
        #     half_spread_ask = half_spread_ask / 2
        # else:
        #     half_spread_ask = Price(2)



        # # To find the quantity of the bids and asks in the market
        # bid_quantity = Quantity(0)
        # for i in range(len(market_data.bids)):
        #     bid_quantity += market_data.bids[i].quantity

        # ask_quantity = Quantity(0)
        # for i in range(len(market_data.asks)):
        #     ask_quantity += market_data.asks[i].quantity
        
        # order_quantity = Quantity(min(int(bid_quantity.value/2),int(ask_quantity.value/2))) #100 is the max order size

        # order_quantity= Quantity(min(abs(order_quantity.value),10))


        return [OrderRequest(self.agent_id, OrderType.BUY, FAIR_VALUE - Price(1.99999), Quantity(10)),
                OrderRequest(self.agent_id, OrderType.SELL, FAIR_VALUE + Price(1.99999), Quantity(10))]
