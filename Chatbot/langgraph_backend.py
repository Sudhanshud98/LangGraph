from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Literal, Annotated
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

llm = ChatOpenAI()

class ChatbotState(TypedDict):
    messages : Annotated[list[BaseMessage], add_messages]

def chat_node(state : ChatbotState):

    messages = state['messages']

    response = llm.invoke(messages)

    return {'messages' : [response]}


checkpointer = InMemorySaver()


graph = StateGraph(ChatbotState)

graph.add_node('chat_node', chat_node)
graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)

workflow = graph.compile(checkpointer = checkpointer)