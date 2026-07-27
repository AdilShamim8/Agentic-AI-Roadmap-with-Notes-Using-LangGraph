FROM langchain/langgraph:latest

WORKDIR /app

COPY pyproject.toml ./
COPY examples/ ./examples/
COPY README.md ./

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "8000"]
