import random
from typing import List, Callable

from core.market import MatchingEngine
from core.types import Timestamp
from core.broker import Broker

from agents.base_agent import TradingAgent

from config import *


class Runner:
    """
    Manages the core logic and execution of a market simulation.
    Orchestrates the interaction between agents, broker, and matching engine.
    """

    def __init__(self, agents: List[TradingAgent], seed: int, on_tick_callback: Callable = lambda x, y: None):
        """
        Initializes the simulation environment

        Args:
            agents: A list of TradingAgent instances to participate
            seed: An integer seed for the random number generator
            on_tick_callback: An optional function to call at the end of each tick
                              that receives the a MarketData snapshot and all AccountStates
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
            print(f"\r--- Tick {self.virtual_clock + 1} ---", end="")

        if prune_age > 0 and self.virtual_clock > 0:
            pruned_orders = self.engine.prune_book(current_timestamp, max_age=prune_age)

            for order in pruned_orders:
                self.broker.remove_order(order)
        
        self.rng.shuffle(self.agents)
        market_data = self.engine.get_market_data()

        for agent in self.agents:
            account_state = self.broker.get_account_state(agent.agent_id)

            # Check registered with broker
            if not account_state:
                raise Exception(f"Agent with id {agent.agent_id} isn't registered with the broker.")
            
            # Get OrderRequests from agent
            requests = agent.propose_trades(market_data, account_state)

            # Skip all OrderRequests if mismatched agent_id
            if sum([agent.agent_id != request.agent_id for request in requests]) != 0:
                continue

            # Process all OrderRequests
            for request in requests:
                risk_violation = self.broker.validate_order(request, market_data)

                # Skip request if risk_violation
                if risk_violation:
                    if verbose and not agent.is_house_agent:
                        print(f"\nRisk violation for Agent {request.agent_id}: {risk_violation.message}")
                else:
                    # Send request to engine
                    order = self.engine.process_order(request, current_timestamp)

                    self.broker.log_order(request)
        
        if self.on_tick_callback:
            self.on_tick_callback(market_data, self.broker.accounts)
        
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

        market_data = self.engine.get_market_data()

        print("\n--- Final Simulation Summary ---")
        print(f"Total Trades Executed: {len(self.engine.trade_log)}")
        
        print("\n--- Final Order Book State ---")
        print(f"# Bids (Buy Orders): {len(market_data.bids)}")
        print("Top 10 Bids:")
        for order in market_data.bids[:10]:
            print(f"  > {order.quantity} @ ${order.price:.2f} (Agent: {order.agent_id})")

        print(f"\n# Asks (Sell Orders): {len(self.engine.asks)}")
        print("Top 10 Asks:")
        for order in market_data.asks[:10]:
            print(f"  > {order.quantity} @ ${order.price:.2f} (Agent: {order.agent_id})")
        
        print("\n--- Final Account States ---")
        mid_price = Price(float(self.engine.trade_log[-1].split("$")[1].split(" ")[0]))

        if self.engine.bids and self.engine.asks:
            mid_price = (market_data.bids[0].price + market_data.asks[0].price)/2

        sorted_accounts = sorted(
            self.broker.accounts.values(), 
            key=lambda x: x.cash + x.position * mid_price,
            reverse=True
        )
        for state in sorted_accounts:
            print(f"  > Agent {state.agent_id.value}:\t Est. Value ${state.cash + state.position * mid_price :,.2f},\t Cash ${state.cash:,.2f},\t Position: {state.position}")

