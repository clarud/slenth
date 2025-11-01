"""
LangGraph + Groq (OpenAI-compatible) demo using LangChain's ChatOpenAI.

Usage:
  - pip install langgraph langchain-openai
  - set GROQ_API_KEY=... (and optionally GROQ_MODEL, e.g. llama3-70b-8192)
  - python scripts/langgraph_groq_demo.py "Your prompt here"
"""

import os
import sys
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    input: str
    output: str


def build_llm() -> ChatOpenAI:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set in environment")

    base_url = "https://api.groq.com/openai/v1"
    model = os.environ.get("GROQ_MODEL", "llama3-70b-8192")

    # ChatOpenAI accepts base_url on recent versions of langchain-openai
    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=0.2,
    )
    return llm


def answer_node_factory(llm: ChatOpenAI):
    def answer_node(state: State) -> State:
        msg = llm.invoke([
            {"role": "system", "content": "You are a concise AI assistant."},
            {"role": "user", "content": state["input"]},
        ])
        return {"output": msg.content}

    return answer_node


def build_graph(llm: ChatOpenAI):
    graph = StateGraph(State)
    graph.add_node("answer", answer_node_factory(llm))
    graph.add_edge(START, "answer")
    graph.add_edge("answer", END)
    return graph.compile()


def main() -> int:
    prompt = " ".join(sys.argv[1:]).strip() or "Explain the importance of fast language models."
    llm = build_llm()
    app = build_graph(llm)
    res = app.invoke({"input": prompt})
    print(res["output"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

