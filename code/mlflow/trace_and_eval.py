"""Trace a tiny RAG app and score it with MLflow GenAI evaluation. No model API key needed.

The "model" is a rule, so the numbers are repeatable. Swap `answer` for a real LLM call later.
Run:  python trace_and_eval.py
"""
import mlflow
from mlflow.entities import SpanType
from mlflow.genai.scorers import scorer

mlflow.set_experiment("support-bot")
DOCS = {"returns.md": "Tents can be returned within 60 days.", "shipping.md": "Express delivery costs 15 dollars."}


@mlflow.trace(span_type=SpanType.RETRIEVER)
def retrieve(question: str) -> list[dict]:
    words = set(question.lower().replace("?", "").split())
    ranked = sorted(DOCS.items(), key=lambda kv: -len(words & set(kv[1].lower().strip(".").split())))
    return [{"page_content": text, "metadata": {"source": name}} for name, text in ranked[:1]]


@mlflow.trace(span_type=SpanType.CHAIN)
def answer(question: str) -> str:
    docs = retrieve(question)
    with mlflow.start_span("compose", span_type=SpanType.LLM) as span:  # a stand-in for the model call
        span.set_inputs({"question": question, "context": docs[0]["page_content"]})
        reply = docs[0]["page_content"]
        span.set_outputs(reply)
    return reply


@scorer
def has_expected_fact(outputs, expectations) -> bool:
    return expectations["must_contain"] in outputs


@scorer
def short_enough(outputs) -> bool:
    return len(outputs) < 80


data = [
    {"inputs": {"question": "How long do I have to return a tent?"}, "expectations": {"must_contain": "60 days"}},
    {"inputs": {"question": "How much does express delivery cost?"}, "expectations": {"must_contain": "15 dollars"}},
    {"inputs": {"question": "Do you sell stoves?"}, "expectations": {"must_contain": "I don't know"}},  # should fail
]
result = mlflow.genai.evaluate(data=data, predict_fn=answer, scorers=[has_expected_fact, short_enough])
print(result.metrics)

traces = mlflow.search_traces(locations=[mlflow.get_experiment_by_name("support-bot").experiment_id], return_type="list")
print("traces stored:", len(traces))
t = traces[0]
print("span names + types in one trace:", [(s.name, str(s.span_type)) for s in t.data.spans])
