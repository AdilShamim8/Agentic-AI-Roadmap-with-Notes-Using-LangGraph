"""
core: framework-agnostic business logic for the customer support system.

Everything in this package is plain Python (+ scikit-learn for search) and
has zero dependency on LangChain/LangGraph. That keeps the "brains" of the
app - data access, intent classification, sentiment detection, and
knowledge-base search - independently testable and reusable, whether they
end up wired into a LangGraph agent, a plain script, or something else
entirely.

The `app/` package wraps these functions as LangChain tools and orchestrates
them with LangGraph.
"""
