"""
Example: Using LangChain + Groq with LangGraph State Management

This example demonstrates the correct pattern for using Groq with LangChain's
ChatOpenAI and LangGraph for state management.
"""

import os
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END


# 1. Define State Type
class State(TypedDict):
    """State for the LangGraph workflow."""
    input: str
    output: str


# 2. Configure ChatOpenAI to point at Groq
llm = ChatOpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
    model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
    temperature=0.2,
)


# 3. Define Node using LCEL invoke pattern
def answer_node(state: State) -> State:
    """
    Node that uses LLM to generate a response.
    
    Uses LangChain's invoke() method which returns a message object
    with the model's reply in msg.content.
    """
    msg = llm.invoke([
        {"role": "system", "content": "You are a concise AI assistant."},
        {"role": "user", "content": state["input"]},
    ])
    
    # msg.content is a string with the model's reply
    return {"output": msg.content}


# 4. Build and Compile Graph
def create_simple_graph():
    """Create a simple LangGraph with one node."""
    graph = StateGraph(State)
    
    # Add node
    graph.add_node("answer", answer_node)
    
    # Define edges
    graph.add_edge(START, "answer")
    graph.add_edge("answer", END)
    
    # Compile the graph
    app = graph.compile()
    
    return app


# 5. Execute the workflow
if __name__ == "__main__":
    # Create the app
    app = create_simple_graph()
    
    # Run the workflow
    result = app.invoke({
        "input": "Explain the importance of fast language models"
    })
    
    print("=" * 60)
    print("OUTPUT:")
    print("=" * 60)
    print(result["output"])
    print("=" * 60)


# ============================================================================
# Advanced Example: AML Transaction Analysis
# ============================================================================

class TransactionState(TypedDict):
    """State for transaction analysis workflow."""
    transaction_data: str
    risk_assessment: str
    compliance_summary: str
    final_decision: str


def analyze_transaction_node(state: TransactionState) -> TransactionState:
    """Analyze transaction for AML risks."""
    msg = llm.invoke([
        {
            "role": "system",
            "content": "You are an AML compliance expert. Analyze transactions for suspicious activity."
        },
        {
            "role": "user",
            "content": f"Analyze this transaction: {state['transaction_data']}"
        }
    ])
    
    return {"risk_assessment": msg.content}


def generate_summary_node(state: TransactionState) -> TransactionState:
    """Generate compliance summary."""
    msg = llm.invoke([
        {
            "role": "system",
            "content": "You are a compliance officer. Summarize risk assessments."
        },
        {
            "role": "user",
            "content": f"Summarize this risk assessment: {state['risk_assessment']}"
        }
    ])
    
    return {"compliance_summary": msg.content}


def make_decision_node(state: TransactionState) -> TransactionState:
    """Make final decision based on analysis."""
    msg = llm.invoke([
        {
            "role": "system",
            "content": "You are a senior compliance analyst. Make final decisions on transactions."
        },
        {
            "role": "user",
            "content": f"Based on this summary, make a decision: {state['compliance_summary']}"
        }
    ])
    
    return {"final_decision": msg.content}


def create_aml_workflow():
    """Create AML analysis workflow."""
    graph = StateGraph(TransactionState)
    
    # Add nodes
    graph.add_node("analyze", analyze_transaction_node)
    graph.add_node("summarize", generate_summary_node)
    graph.add_node("decide", make_decision_node)
    
    # Define workflow
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "summarize")
    graph.add_edge("summarize", "decide")
    graph.add_edge("decide", END)
    
    return graph.compile()


def run_aml_example():
    """Run AML workflow example."""
    app = create_aml_workflow()
    
    result = app.invoke({
        "transaction_data": """
        Transaction ID: TXN-12345
        Amount: $50,000 USD
        Sender: John Doe (US)
        Receiver: ABC Corp (Cayman Islands)
        Purpose: Consulting services
        """
    })
    
    print("\n" + "=" * 60)
    print("AML ANALYSIS WORKFLOW RESULTS:")
    print("=" * 60)
    print("\n1. RISK ASSESSMENT:")
    print(result.get("risk_assessment", "N/A"))
    print("\n2. COMPLIANCE SUMMARY:")
    print(result.get("compliance_summary", "N/A"))
    print("\n3. FINAL DECISION:")
    print(result.get("final_decision", "N/A"))
    print("=" * 60)


if __name__ == "__main__":
    # Run simple example
    print("\n" + "=" * 60)
    print("SIMPLE EXAMPLE:")
    print("=" * 60)
    
    app = create_simple_graph()
    result = app.invoke({
        "input": "Explain the importance of fast language models"
    })
    print(result["output"])
    
    # Run AML example
    print("\n" + "=" * 60)
    print("AML WORKFLOW EXAMPLE:")
    print("=" * 60)
    run_aml_example()
