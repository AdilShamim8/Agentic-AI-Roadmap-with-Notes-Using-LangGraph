> # `What is LangGraph?`

LangGraph is an orchestration framework for building **intelligent**, **stateful**, and **multi-step** LLM workflows.

Key ideas:

- Supports **parallelism**, **loops**, **branching**, **memory**, and **resumability**
- Designed for **agentic** and **production-grade** AI systems
- Models logic as a **graph**, not a linear chain

In LangGraph:
- **Nodes** represent tasks
- **Edges** represent routing logic
- **State** represents shared memory flowing through the system

---

## What Are LLM Workflows?

LLM workflows are **step-by-step processes** used to build complex LLM-powered applications.

### Core Principles

1. Each step performs a **distinct task**
   - Prompting
   - Reasoning
   - Tool calling
   - Memory access
   - Decision-making

2. Workflows are not always linear

They can be:
- Linear
- Parallel
- Branched
- Looped

3. These patterns enable:
- Retries
- Multi-agent coordination
- Tool-augmented reasoning
- Self-improving systems

---

## Common LLM Workflow Patterns

### 1. Prompt Chaining (Conceptual)

```

In → LLM Call 1 → Output 1 → Gate
├─ If Pass → LLM Call 2 → Output 2 → LLM Call 3 → Out
└─ If Fail → Exit

```

**Explanation:**
- Output from one step decides the next step
- Simple branching logic
- Still mostly linear

---

### 2. Routing & Parallelization

```

In → LLM Router
├─ LLM Call 2
├─ LLM Call 3
└─ LLM Call 4
↓
Aggregator → Out

```

**Why this matters:**
- Multiple tasks run **in parallel**
- Faster execution
- Useful for evaluation and analysis tasks

---

## Routing and Orchestrator Workflows

### Parallelization Pattern

```

In → Router
├─ LLM Call 1
├─ LLM Call 2
└─ LLM Call 3
↓
Aggregator → Out

```

The aggregator combines results from parallel branches before producing output.

---

### Orchestrator–Workers Pattern

```

In → Orchestrator
├─ Worker LLM 1
├─ Worker LLM 2
└─ Worker LLM 3
↓
Synthesizer → Out

```

**Mental model:**
- Orchestrator decides *what work to do*
- Workers execute tasks
- Synthesizer merges results

This is a **core agentic architecture**.

---

## Evaluator–Optimizer Loop

```

In → Generator → Evaluator
↑         ↓
Feedback   Accepted?

````

### Flow Explanation

- Generator produces a solution
- Evaluator checks quality
- If rejected, feedback is sent back
- Loop continues until accepted

Used in:
- Self-improving agents
- High-quality content generation
- Autonomous refinement systems

---

## Graphs, Nodes, and Edges (Concrete Example)

### Example: Essay Evaluation System

The system:
- Generates an essay topic
- Collects student input
- Evaluates in parallel
- Decides whether to approve or request revision

---

### Nodes in the Graph

#### 1. GenerateTopic
- Generates a UPSC-style essay topic

#### 2. CollectEssay
- Collects student submission

#### 3. EvaluateEssay (Parallel Block)

Runs three evaluations in parallel:
- **EvaluateDepth**
- **EvaluateLanguage**
- **EvaluateClarity**

#### 4. AggregateResults
- Combines scores into a total score

#### 5. ConditionalRouting
- If score ≥ threshold → `ShowSuccess`
- Else → `GiveFeedback`

#### 6. GiveFeedback
- Provides targeted improvement suggestions

#### 7. CollectRevision (Optional Loop)
- Student revises essay
- Loops back to evaluation

#### 8. ShowSuccess
- Ends the workflow

---

## State in LangGraph

State is the **shared memory** that flows through the graph.

Nodes do **not pass variables directly** —  
they **read and update state**.

### Example State Schema

```python
essay_text:        str
topic:             str
depth_score:       int
language_score:    int
clarity_score:     int
total_score:       int
feedback:          Annotated[list[str], add]
evaluation_round:  int
````

---

## Reducers

Reducers define **how state updates are applied**.

Each state field can have its own reducer:

* Replace value
* Merge data
* Append to lists
* Accumulate counters

Reducers make LangGraph:

* Safe for parallel execution
* Deterministic
* Easy to reason about

---

## LangGraph Execution Model

### 1. Graph Definition

You define:

* State schema
* Nodes (functions)
* Edges (routing rules)

---

### 2. Compilation

```python
graph.compile()
```

This:

* Validates the graph
* Prepares it for execution

---

### 3. Invocation

```python
graph.invoke(initial_state)
```

The initial state enters the graph.

---

### 4. Super-Steps Begin

Execution happens in **rounds (super-steps)**.

In each round:

* All active nodes run **in parallel**
* Each node returns state updates

---

### 5. Message Passing & Node Activation

* Messages flow along edges
* Nodes receiving messages become active in the next round

---

### 6. Halting Condition

Execution stops when:

* No nodes are active
* No messages are in transit

---

## Key Mental Model

> **LangGraph is a state machine powered by LLMs.**

* Nodes = actions
* Edges = decisions
* State = memory
* Super-steps = controlled execution
