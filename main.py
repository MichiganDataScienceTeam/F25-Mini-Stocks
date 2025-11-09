import random
from typing import List

from simulation.runner import Runner
from core.types import AgentId, Price
from agents.base_agent import TradingAgent
from agents.house_agents import BadMarketMaker, NoiseTraderBot, RandomReverter, MysteryBot

# !!! IMPORT YOUR BOTS HERE !!!

if __name__ == "__main__":
    # --- Simulation Configuration ---
    SIMULATION_SEED = 2025
    NUM_TICKS = 10_000
    DEFAULT_FAIR_VALUE = Price(100)
    
    # House agents
    num_market_makers = 3
    num_noise_traders = 20
    num_mystery_bots = 5

    # User agent

    # !!! ADD YOUR AGENT HERE !!!
    user_agent = None  # << Replace None with your agent
    # !!! ADD YOUR AGENT HERE !!!

    # Setup
    config_rng = random.Random(SIMULATION_SEED)
    all_agents: List[TradingAgent] = []

    # --- Add agents ---

    all_agents.append(user_agent) if user_agent else None

    for i in range(1, num_market_makers+1):
        all_agents.append(
            BadMarketMaker(
                agent_id = AgentId(i*100),
                default_fair_value = DEFAULT_FAIR_VALUE
            )
        )

    for i in range(1, num_noise_traders+1):
        all_agents.append(
            NoiseTraderBot(
                agent_id = AgentId(-i*100),
                trade_probability = 0.8,
                max_trade_size = 75
            )
        )
    
    for i in range(num_market_makers+1, num_mystery_bots+num_market_makers+2):
        all_agents.append(
            MysteryBot(
                agent_id = AgentId(i*100),
                default_fair_value = DEFAULT_FAIR_VALUE,
            )
        )

    # --- Execution ---
    sim = Runner(agents=all_agents, seed=SIMULATION_SEED)

    sim.run(
        num_ticks = NUM_TICKS,
        verbose = True
    )

