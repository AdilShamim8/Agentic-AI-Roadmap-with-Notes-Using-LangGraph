## Why Sequential Workflows Matter

Sequential workflows are the **foundation of all agentic systems**.

* They are the **simplest and most predictable** workflow type
* Easy to debug and reason about
* Ideal for **prompt chaining**, **data preprocessing**, and **step-by-step reasoning**
* Serve as a **base pattern** before introducing branching, loops, or parallelism

If you understand sequential workflows well, **everything else in LangGraph becomes easier**.

---

## What is a Sequential Workflow?

A sequential workflow is a **linear graph**:

```
Start → Step 1 → Step 2 → Step 3 → End
```

* Each node runs **only after** the previous node completes
* There are **no branches or loops**
* State flows forward and gets updated at each step

---

## Real-World Intuition

Think of cooking instant noodles:

1. Boil water
2. Add noodles
3. Add spices
4. Serve

You **cannot skip or reorder** steps. This is exactly how a sequential workflow behaves.

---

## Typical Use Cases

Sequential workflows are perfect for:

* Prompt → Refine → Format
* Input → Analyze → Summarize
* User Query → Retrieve Context → Generate Answer
* Data Cleaning → Feature Extraction → Prediction

---

## Sequential Prompt Chaining (Concept)

```
User Input
   ↓
LLM Call 1 (Understand Intent)
   ↓
LLM Call 2 (Reason / Expand)
   ↓
LLM Call 3 (Final Answer)
```

Each step improves or transforms the output from the previous step.

---

## Core Components in LangGraph Sequential Flow

### 1. State

State is the **shared memory** passed between nodes.

Example state:

```
query: str
intent: str
reasoning: str
final_answer: str
```

Each node **reads from state and writes updates back to it**.

---

### 2. Nodes

Nodes are **functions** that:

* Take the current state
* Perform a task (LLM call, logic, tool usage)
* Return updates to the state

Example node responsibilities:

* Node 1: Extract intent from user query
* Node 2: Perform reasoning based on intent
* Node 3: Generate final response

---

### 3. Edges

Edges define **execution order**.

In sequential workflows:

```
Node A → Node B → Node C
```

There is **only one path forward**.

---

## Minimal Sequential Graph (Conceptual)

```
ENTRY → UnderstandQuery → Reason → Answer → END
```

* ENTRY starts the graph
* END stops execution

---

## Execution Behavior

LangGraph executes sequential workflows as follows:

1. Entry node receives initial state
2. Node runs and updates state
3. Updated state flows to next node
4. Process continues until END

No parallelism. No branching. No retries.

---

## Sequential Workflow Example (Story Style)

**Task:** Build an AI tutor that answers questions clearly.

### Step-by-step Graph

1. **CollectQuestion**

   * Reads user question

2. **AnalyzeQuestion**

   * Identifies topic and difficulty

3. **GenerateExplanation**

   * Produces a structured explanation

4. **FormatAnswer**

   * Makes response beginner-friendly

```
CollectQuestion → AnalyzeQuestion → GenerateExplanation → FormatAnswer
```

---

## Strengths of Sequential Workflows

* Simple mental model
* Deterministic execution
* Easy testing & debugging
* Ideal for notebooks and demos

---

## Limitations

Sequential workflows are **not enough** when:

* You need parallel evaluations
* You need retries or feedback loops
* You need dynamic routing

That’s where **branching, loops, and agentic graphs** come in (coming next days 👀).

---

## Key Takeaways

* Sequential workflows are **linear LangGraph graphs**
* Nodes execute **one after another**
* State flows forward and gets refined
* This is the **starting point** for all agentic systems