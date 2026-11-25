from typing import TypedDict, Any

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

from app.services.procurement_workflow import (
    run_procurement_workflow
)


class ProcurementState(TypedDict, total=False):

    product_or_service: str
    location: str
    max_results: int

    procurement_result: dict

    approval_status: str
    approval_comments: str


# STEP 1: Execute procurement workflow

async def procurement_node(state: ProcurementState):

    result = await run_procurement_workflow(
        product_or_service=state["product_or_service"],
        location=state["location"],
        max_results=state["max_results"]
    )

    return {
        "procurement_result": result.model_dump()
    }


# STEP 2: Human approval gate

def approval_node(state: ProcurementState):

    decision = interrupt({
        "message": "Human approval required.",
        "procurement_result": state["procurement_result"]
    })

    return {
        "approval_status": decision["decision"],
        "approval_comments": decision.get("comments", "")
    }


# STEP 3: Finalize workflow

def finalize_node(state: ProcurementState):

    return {
        "approval_status": state["approval_status"]
    }


# STEP 4: Build graph

builder = StateGraph(ProcurementState)

builder.add_node("procurement", procurement_node)
builder.add_node("human_approval", approval_node)
builder.add_node("finalize", finalize_node)

builder.add_edge(START, "procurement")
builder.add_edge("procurement", "human_approval")
builder.add_edge("human_approval", "finalize")
builder.add_edge("finalize", END)


# In-memory checkpointing for development

memory = MemorySaver()

approval_graph = builder.compile(
    checkpointer=memory
)


# STEP 5: Start workflow

async def start_approval_workflow(
    product_or_service: str,
    location: str,
    max_results: int,
    thread_id: str
):

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = await approval_graph.ainvoke(
        {
            "product_or_service": product_or_service,
            "location": location,
            "max_results": max_results
        },
        config=config
    )

    return result


# STEP 6: Resume workflow after human decision

async def resume_approval_workflow(
    thread_id: str,
    decision: str,
    comments: str = ""
):

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = await approval_graph.ainvoke(
        Command(
            resume={
                "decision": decision,
                "comments": comments
            }
        ),
        config=config
    )

    return result