## 1. What Are Iterative Workflows?

An iterative workflow repeatedly executes a set of nodes until:

* A goal is achieved
* A condition is met
* A maximum number of iterations is reached

This is **different from sequential or parallel workflows** because it introduces **dynamic repetition**.

```
Start → Task → Decision → [if not done] → Task → ... → End
```

---

## 2. Why Iterative Workflows Matter

* Enable agents to **self-correct**
* Support **reflection and learning**
* Allow **error handling and retries**
* Combine with conditional + parallel workflows for **complex behaviors**

Real agents **rarely get it right the first time** — iteration is key.

---

## 3. Mental Model

Think of iterative workflows as:

> "Try → Evaluate → Adjust → Try again"

Example: Writing an essay

1. Generate draft
2. Check for grammar, clarity, depth
3. Apply feedback
4. Repeat until acceptable

---

## 4. Conceptual Diagram of a Loop

```
Start → Task → Decision → Loop?
          ↑             ↓
          ←------------
          ↓
         End
```

* Task: Performs action (e.g., generate text)
* Decision: Checks state to decide next step (loop or end)
* Loop: Sends state back to Task for another iteration

---

## 5. Combining Loops with Conditional Workflows

Loops often **depend on conditions**.

```
Evaluate Essay → Decision Node
       ├── Score >= 12 → Success → End
       ├── Score >= 8 → Feedback → End
       └── Score < 8 → Revise Essay → Loop back to Evaluate Essay
```

* Conditional node decides whether to **exit or loop**
* Iterative workflow allows repeated improvement

---

## 6. Iterative Workflows + Parallel Nodes

Loops can also **run parallel evaluations in each iteration**:

```
Essay → Parallel Evaluation → Aggregate → Decision → Loop?
```

* Parallel evaluation ensures **multi-perspective analysis**
* Decision node controls iteration
* Aggregator merges results for next loop

---

## 7. Use Cases in Agentic AI

1. **Self-improving text generation**

   * Draft → Evaluate → Refine → Repeat
2. **Autonomous coding agents**

   * Generate code → Test → Fix errors → Repeat
3. **Research assistants**

   * Query → Evaluate evidence → Summarize → Iterate
4. **Multi-agent simulations**

   * Agents communicate → Update state → Retry strategies

---

## 8. State Management in Loops

* Shared state persists across iterations
* Reducers determine **how new updates affect existing state**

Example:

```python
iteration: int  # tracks loop count
draft: str      # updated each iteration
feedback: list[str]  # accumulate feedback
score: float   # updated each iteration
```

* **iteration counter** prevents infinite loops
* **feedback list** accumulates insights

---

## 9. Best Practices

* Set **max iterations** to prevent infinite loops
* Use **clear decision criteria** to exit loops
* Combine with **conditional routing** for safety
* Combine with **parallelism** for efficiency
* Log iterations for debugging and learning

---

## 10. Key Takeaways

* Iterative workflows let agents **repeat, reflect, and improve**
* Loops can combine **conditional and parallel workflows**
* State + reducers ensure safe and predictable iteration
* Essential for **autonomous, agentic behavior**