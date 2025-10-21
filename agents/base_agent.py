from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

from core.market import MarketData
from core.types import OrderRequest, AgentId

if TYPE_CHECKING:
    from core.broker import AccountState


class TradingAgent(ABC):
    """
    An abstract base class that defines the interface for all TradingAgents.

    Must implement propose_trades
    """

    def __init__(self, agent_id: AgentId):
        """
        Initializes the TradingAgent with its unique ID.

        Args:
            agent_id: The unique identifier for this TradingAgent
        """

        self.agent_id = agent_id
        self.is_house_agent = False

    @abstractmethod
    def propose_trades(self, market_data: MarketData, my_account_state: "AccountState") -> List[OrderRequest]:
        """
        This method is called exactly once at every simulation tick.
        The implementation should analyze the market data

        Args:
            market_data: The current state of the matching engine
            my_account_state: The current state of this agent's account

        Returns:
            A list of OrderRequest objects to be submitted to the market
            or an empty list if the algorithm decides not to trade
        """

        pass

