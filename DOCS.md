# F25 Mini-Stocks Documentation

This project contains a large amount of custom infrastructure that would be burdensome to understand at a granular level but is essential to understand at a functional level.

This document aims to clarify the design choices of the core infrastructure and assist in the implementation of trading agents and analysis scripts.

## Contents

* [Simulation Design](#simulation-design)
    * [Overview](#overview)
    * [Trading Agents](#trading-agents)
    * [Broker](#broker)
    * [Matching Engine](#matching-engine)
    * [Simulator](#simulator)
* [Custom Types](#custom-types)
    * TBD
* [Implementation Guide](#implementation)
    * TBD

## Simulation Design

### Overview

The simulation design can be briefly summarized with the following diagram

![Diagram alt text (TODO)](docs-assets/mini-stocks-diagram.png)

There are 4 core functional components:

* **Trading Agents:** Processes market data and submits order requests

* **Broker:** Tracks the account states (cash, position) of each agent and validates order requests

* **Matching Engine:** Manages the order books and executes orders

* **Simulation**

**NOTE:** Currently, only a limited version of this design that uses exactly one order book is implemented.

### Trading Agents

Trading agents are the most flexible component of the market.

There are, however, a few properties of trading agents that this project enforces:

* Uniqueness

* Can access information about every resting order

* Can access information about its own account state

* Can request any number of any type of order

Enforcement of these properties is through the [abstract base class](https://www.geeksforgeeks.org/python/abstract-classes-in-python/) (ABC) `TradingAgent` in `agents/base_agent.py`.

This project requires that the implementation of every trading agent is its own class that [extends](https://www.w3schools.com/python/python_inheritance.asp) the `TradingAgent` class, forcing the inheritence of the interface that guarantees the above properties.

User-defined `TradingAgent`s are intended to be located in the `user_agents` directory, though this is neither enforced nor required.

As an example, we can implement the trivial trading agent that never places orders:

```py
# user_agents/trivial_agent.py
from agents.base_agent import TradingAgent

class TrivialAgent(TradingAgent):
    def propose_trades(self, market_data, my_account_state):
        return []
```

Notice that `TrivialAgent` doesn't need to implement `__init__` because `TradingAgent` already implements a minimal `__init__` and the design of this particular agent doesn't need any additional parameters.

Despite the very simple implementation, the `TrivialAgent` is completely functional:

```py
# Other imports are hidden
from core.types import AgentId
from user_agents import TrivialAgent

market_data = ... # Assume a valid MarketData object
account_state = ... # Assume a valid AccountState object

my_agent = TrivialAgent(AgentId(1))

# This correctly gets my_agent's OrderRequests
order_requests = my_agent.propose_trades(
    market_data,
    account_state
)
```

### Broker

The broker is the only line of defense between an illegal or impossible order request and the market.

**NOTE:** In real markets, brokers have a much broader set of important responsibilities than just being a gatekeeper of the market. Implementing all of these complexities would have minimal returns for this project, so we use a heavily limited adaptation of the concept of a broker.

The broker is entirely implemented in `core/broker.py`, which contains the main `Broker` class, supporting [dataclasses](https://www.geeksforgeeks.org/python/data-classes-in-python-an-introduction/) (`AccountState` and `RiskViolation`), and the `RiskViolationType` [enum](https://www.geeksforgeeks.org/python/enum-in-python/).

The broker enforces the following constraints on every `OrderRequest` submitted by a `TradingAgent`:

* Orders may not exceed a predetermined size

* Orders may not allow the possibility of a `TradingAgent` trading with itself

* Bids may not cost more to execute than the `TradingAgent`'s available cash

* Orders may not allow the possibility a `TradingAgent` accumulating a position greater than `n` or less than `-n` for some predetermined quantity `n`

When the `Broker` detects a violation of any of these constraints, it produces a `RiskViolation` object that is passed to the market and is made available to the user.

A side effect of enforcing the position limits constraint is careful tracking of each `TradingAgent`'s cash and position, which is itself a productive task.
As a result, the `Broker` is also the internal recordkeeper for all `AccountState`s.
This, however, is an implementation detail and isn't important to a user developing `TradingAgent`s.

Users designing and implementing `TradingAgent`s should be able to do so without knowledge of the specific implementation of `Broker`, though it is very helpful to know which constraints it enforces.

### Matching Engine

The matching engine maintains an ordered record of all `Orders` in an implementation of a [limit order book](https://optiver.com/explainers/orders-and-the-order-book/) (LOB) and matches orders accoring to price-time priority.

**NOTE:** The implementation of the matching engine in its current state is very inefficient and will likely be significantly redesigned soon. Fortunately, these changes will not change the function or interface of the engine, so everything in this section will still be true after any changes. (UPDATE: most of the matching engine issues have been resolved. There are still a few issues left, but the focus is currently on improving the Broker.)

[THIS SECTION IS IN PROGRESS]

### Simulator

[THIS SECTION IS IN PROGRESS]

## Custom Types

[THIS SECTION IS IN PROGRESS]

## Implementation Guide

[THIS SECTION IS IN PROGRESS]
