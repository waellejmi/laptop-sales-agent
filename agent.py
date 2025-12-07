import os
from typing import Annotated, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage
from langchain_groq import ChatGroq
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langgraph.graph import START, MessagesState, StateGraph, add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()


TOOLS = []


class LaptopSpecification(TypedDict, total=False):
    model_name: str
    brand: str
    cpu: str
    cpu_cores: int
    cpu_threads: int
    ram: int
    ssd_gb: int
    hdd_gb: int
    os: str
    gpu: str
    gpu_vram_gb: int
    screen_size_in: float
    resolution_w: int
    resolution_h: int
    resolution_type: str
    spec_score: int
    price_euro: float


class UserRequestClassification(TypedDict):
    usage_profile: Literal["gaming", "student", "basic", "workstation"]
    user_emphasis: Optional[
        list[Literal["cpu_tier", "gpu_tier", "ram", "ssd_present", "price"]]
    ]
    filters: Optional[LaptopSpecification]


class SalesAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

    classfication: UserRequestClassification | None

    recommended_laptops: list[dict] | None

    final_response: str


def build_graph(provider: str = "groq"):
    if provider == "groq":
        GROQ_API_KEY = os.getenv("GROQ_KEY")
        llm = ChatGroq(model="qwen/qwen3-32b", api_key=GROQ_API_KEY, temperature=0)
    elif provider == "huggingface":
        HF_TOKEN = os.getenv("HF_TOKEN")
        llm = ChatHuggingFace(
            llm=HuggingFaceEndpoint(
                repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                task="text-generation",
                max_new_tokens=1024,
                do_sample=False,
                repetition_penalty=1.03,
                temperature=0,
                huggingfacehub_api_token=HF_TOKEN,
            ),
            verbose=True,
        )

    chat_with_tools = llm.bind_tools(TOOLS)

    def assistant(state: MessagesState):
        return {
            "messages": [chat_with_tools.invoke(state["messages"])],
        }

    builder = StateGraph(MessagesState)
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(TOOLS))

    builder.add_edge(START, "assistant")
    builder.add_conditional_edges("assistant", tools_condition)
    builder.add_edge("tools", "assistant")

    walfred = builder.compile()
    return walfred
