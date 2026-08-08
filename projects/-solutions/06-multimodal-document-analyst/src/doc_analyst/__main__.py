"""Allow `python -m doc_analyst ...` as an alias for `doc-analyst ...`."""
from .cli import app

if __name__ == "__main__":
    app()
