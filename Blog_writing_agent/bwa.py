from __future__ import annotations

import operator
from typing import TypedDict, List, Annotated

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pathlib import Path
from IPython.display import Image

class Task(BaseModel):
    id : int
    title : str
    brief : str = Field(..., description = "What to cover")

class Plan(BaseModel):
    blog_title : str
    task : str

class State(TypedDict):
    topic : str
    plan : Plan
    sections : Annotated[list[str], operator.add] # we are using reducer function (operator.add) to concatinate the responses from each worker
    final: str

llm = ChatOpenAI(model ='gpt-4.1-mini')

def orchestrator(state : State) -> dict:
    plan = llm.with_structured_output(Plan).invoke(
        [
            SystemMessage(
                content = (
                    'Create a blog plan with 5-7 sections on the following topic.'
                )
            ),
            HumanMessage(content = f"Topic: {state['topic']}"),
        ]
    )
    return {'plan' : plan}

# this fuction assigns task to workers
def fanout(state : State):
    return [Send('Worker', {'task':task, 'topic':state['topic'], 'plan':state['plan']})
            for task in state['plan'].task]

def worker(payload: dict) -> dict:

    # payload contains what we sent
    task = payload["task"]
    topic = payload["topic"]
    plan = payload["plan"]

    blog_title = plan.blog_title

    section_md = llm.invoke(
        [
            SystemMessage(content="Write one clean Markdown section."),
            HumanMessage(
                content=(
                    f"Blog: {blog_title}\n"
                    f"Topic: {topic}\n\n"
                    f"Section: {task.title}\n"
                    f"Brief: {task.brief}\n\n"
                    "Return only the section content in Markdown."
                )
            ),
        ]
    ).content.strip()

    return {"sections": [section_md]}

def reducer(state : State) -> dict:
    title = state['plan'].blog_title
    body = '\n\n'.join(state['sections']).strip()

    final_md = f'# {title}\n\n{body}\n'

    # ---- save to file ----
    filename = title.lower().replace(" ", "_") + ".md"
    output_path = Path(filename)
    output_path.write_text(final_md, encoding="utf-8")

    return {"final": final_md}

builder = StateGraph(State)

builder.add_node('orchestrator', orchestrator)
builder.add_node('worker', worker)
builder.add_node('reducer', reducer)

builder.add_edge(START, 'orchestrator')
builder.add_conditional_edges('orchestrator', fanout,  ['worker'])
builder.add_edge('worker', 'reducer')
builder.add_edge('reducer', END)

app = builder.compile()

# print(Image(app.get_graph().draw_mermaid_png()))

print(app.invoke({'topic' : 'Write a blog on Self Attention', 'sections' : []}))