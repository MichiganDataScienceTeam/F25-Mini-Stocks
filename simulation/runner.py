import random
from typing import List, Callable

from core.market import MatchingEngine, OrderRejected
from core.types import Timestamp
from core.broker import Broker

from agents.base_agent import TradingAgent

from config import *


class Runner:
    """
    Manages the core logic and execution of a market simulation.
    Orchestrates the interaction between agents, broker, and matching engine.
    """

    def __init__(self, agents: List[TradingAgent], seed: int, on_tick_callback: Callable = lambda x: None):
        """
        Initializes the simulation environment

        Args:
            agents: A list of TradingAgent instances to participate
            seed: An integer seed for the random number generator
            on_tick_callback: An optional function to call at the end of each tick
                              that receives the a MarketData snapshot as the argument
        """
        self.broker = Broker(agents)
        
        self.engine = MatchingEngine(on_trade_callback=self.broker.settle_trade)

        self.agents = agents
        self.rng = random.Random(seed)
        self.virtual_clock = 0
        self.on_tick_callback = on_tick_callback

    def _run_tick(self, verbose: bool = True, prune_age: int = DEFAULT_PRUNE_AGE) -> None:
        """
        (INTERNAL) Runs a single tick of the simulation

        Args:
            verbose: Whether to always announce the tick
            prune_age: The max age (in ticks) an Order can be before
                       being discarded or -1 to keep all Orders
            debug_callback: Optional callback for debugging/logging
        
        Returns:
            None
        """

        current_timestamp = Timestamp(self.virtual_clock)

        if verbose:
            print(f"\r--- Tick {self.virtual_clock} ---", end="")

        if prune_age > 0 and self.virtual_clock > 0 and self.virtual_clock % prune_age == 0:
            self.engine.prune_book(current_timestamp, max_age=prune_age)
        
        self.rng.shuffle(self.agents)
        market_data = self.engine.get_market_data()

        for agent in self.agents:
            account_state = self.broker.get_account_state(agent.agent_id)
            if account_state:
                requests = agent.propose_trades(market_data, account_state)
                for request in requests:
                    # Pre-trade risk check
                    risk_violation = self.broker.validate_order(request, market_data)
                    if risk_violation:
                        if verbose:
                            print(f"\nRisk violation for Agent {request.agent_id}: {risk_violation.message}")
                        continue  # Skip this order
                    
                    # Order passed risk checks, submit to matching engine
                    result = self.engine.process_order(request, current_timestamp)
                    if isinstance(result, OrderRejected) and verbose:
                        print(f"\nOrder rejected for Agent {request.agent_id}: {result.reason}")
        
        if self.on_tick_callback:
            self.on_tick_callback(market_data)

    def run(self, num_ticks: int, verbose: bool = True) -> None:
        """
        Runs the main simulation loop for a specified number of ticks.

        Args:
            num_ticks: The number of ticks to run
            verbose: Whether to print info and summary statistics
        
        Returns:
            None
        """

        if verbose:
            print(f"--- Starting Simulation (Running for {num_ticks} ticks) ---")
        
        for tick in range(num_ticks):
            self.virtual_clock = tick
            self._run_tick(verbose)

        if not verbose:
            return

        print("\n\n--- Simulation Complete ---")
        self.print_summary()

    def print_summary(self) -> None:
        """
        Prints a summary of the simulation results.

        Args:
            None
        
        Returns:
            None
        """

        print("\n--- Final Simulation Summary ---")
        print(f"Total Trades Executed: {len(self.engine.trade_log)}")
        
        print("\n--- Final Order Book State ---")
        print(f"# Bids (Buy Orders): {len(self.engine.bids)}")
        print("Top 10 Bids:")
        for order in self.engine.bids[:10]:
            print(f"  > {order.quantity} @ ${order.price:.2f} (Agent: {order.agent_id})")

        print(f"\n# Asks (Sell Orders): {len(self.engine.asks)}")
        print("Top 10 Asks:")
        for order in self.engine.asks[:10]:
            print(f"  > {order.quantity} @ ${order.price:.2f} (Agent: {order.agent_id})")
        
        print("\n--- Final Account States ---")
        sorted_accounts = sorted(
            self.broker.accounts.values(), 
            key=lambda x: x.cash, 
            reverse=True
        )
        for state in sorted_accounts:
            print(f"  > Agent {state.agent_id.value}:\t Cash ${state.cash:,.2f}, Position: {state.position}")

