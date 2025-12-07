import os
from typing import Annotated, Any, Literal, Optional, TypedDict

import pandas as pd
from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph.types import Command
from pydantic import BaseModel

from filter import filter_laptops
from scoring import compute_scores, get_weights

load_dotenv()


class LaptopSpecification(BaseModel):
    model_name: Optional[str] = None
    brand: Optional[str] = None
    cpu: Optional[str] = None
    cpu_cores: Optional[int] = None
    cpu_threads: Optional[int] = None
    ram: Optional[int] = None
    ssd_gb: Optional[int] = None
    hdd_gb: Optional[int] = None
    os: Optional[str] = None
    gpu: Optional[str] = None
    gpu_vram_gb: Optional[float] = None
    screen_size_in: Optional[float] = None
    resolution_w: Optional[int] = None
    resolution_h: Optional[int] = None
    resolution_type: Optional[str] = None
    spec_score: Optional[int] = None
    price_euro: Optional[float] = None


class UserRequestClassification(BaseModel):
    usage_profile: Literal["gaming", "student", "basic", "workstation"]
    user_emphasis: Optional[
        list[Literal["cpu_tier", "gpu_tier", "ram", "ssd_present", "price"]]
    ] = None
    filters: Optional[LaptopSpecification] = None


class SalesAgentState(TypedDict):
    user_input: str

    classification: dict[str, Any] | None

    filtered_laptops: list[dict[str, Any]] | None

    recommended_laptops: list[dict[str, Any]] | None

    final_response: str | None

    messages: Annotated[list[AnyMessage], add_messages]


def build_graph(provider: str = "groq"):
    if provider == "groq":
        GROQ_API_KEY = os.getenv("GROQ_KEY")
        llm = ChatGroq(model="qwen/qwen3-32b", api_key=GROQ_API_KEY, temperature=0.5)
    elif provider == "huggingface":
        HF_TOKEN = os.getenv("HF_TOKEN")
        llm = ChatHuggingFace(
            llm=HuggingFaceEndpoint(
                repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                task="text-generation",
                max_new_tokens=1024,
                do_sample=False,
                repetition_penalty=1.03,
                temperature=0.5,
                huggingfacehub_api_token=HF_TOKEN,
            ),
            verbose=True,
        )

    def read_user_prompt(state: SalesAgentState) -> dict:
        """Extract and parse content here i need to add an input fucntion"""
        # maybe i add read from a text file or live from a cli
        return {
            "messages": [
                HumanMessage(content=f"Processing User Input: {state['user_input']}")
            ]
        }

    def classify_intent(
        state: SalesAgentState,
    ) -> Command[Literal["get_filtered_laptops", "get_recommended_laptops"]]:
        """Use LLM to parse user prompt to get his usage profile, his emphasis and hard filters."""

        structured_llm = llm.with_structured_output(UserRequestClassification)

        classification_prompt = f"""
        Analyze this customer message and classify it:

        User Message: {state["user_input"]}

        Provide:
        1. usage_profile: One of ["gaming", "student", "basic", "workstation"]
        2. user_emphasis: List of emphasized features from ["cpu_tier", "gpu_tier", "ram", "ssd_present", "price"], or null
        3. filters: Dictionary of specific requirements mentioned or null if none specified

        Only include filters that are explicitly mentioned by the user.
        """

        classification = structured_llm.invoke(classification_prompt)

        if classification.filters:
            goto = "get_filtered_laptops"
        else:
            goto = "get_recommended_laptops"

        return Command(
            update={"classification": classification.model_dump()}, goto=goto
        )

    def get_filtered_laptops(
        state: SalesAgentState,
    ) -> Command[Literal["get_recommended_laptops", "inform_user_no_laptops"]]:
        """Filter laptops based on user criteria."""
        classification = state.get("classification", {})
        filters = classification.get("filters", {})
        try:
            filtered_laptops_df = filter_laptops(**filters)
            if filtered_laptops_df.empty:
                return Command(
                    update={"filtered_laptops": []}, goto="inform_user_no_laptops"
                )
            filtered_laptops = filtered_laptops_df.to_dict(orient="records")
            return Command(
                update={"filtered_laptops": filtered_laptops},
                goto="get_recommended_laptops",
            )
        except Exception as e:
            return Command(
                update={
                    "filtered_laptops": [],
                    "final_response": f"Filtering Error: {str(e)}",
                },
                goto="inform_user_no_laptops",
            )

    def inform_user_no_laptops(state: SalesAgentState) -> dict:
        """Inform the user that no laptops matched their criteria."""
        return {
            "final_response": (
                "Unfortunately, no laptops match your specified criteria. "
                "Please consider adjusting your requirements."
            )
        }

    def get_recommended_laptops(
        state: SalesAgentState,
    ) -> Command[Literal["explain_reccomandations"]]:
        """Apply user pofile and emphasis to recommend laptops."""

        classification = state.get("classification", {})
        usage_profile = classification.get("usage_profile", "basic")
        user_emphasis = classification.get("user_emphasis", [])
        filtered_laptops = state.get("filtered_laptops", pd.DataFrame())

        profile_weights = get_weights(usage_profile, user_emphasis)

        if filtered_laptops is None or len(filtered_laptops) == 0:
            df = pd.read_csv("./data/laptops_enhanced.csv")
        else:
            df = pd.DataFrame(filtered_laptops)

        top3_ranked = compute_scores(df, profile_weights).head(3)
        recommended_laptops = top3_ranked.to_dict(orient="records")

        return Command(
            update={"recommended_laptops": recommended_laptops},
            goto="explain_reccomandations",
        )

    def explain_reccomandations(
        state: SalesAgentState,
    ) -> Command[Literal["send_reply"]]:
        """Generate a final response explaining the recommendations to the user."""
        reccomended_laptops = state.get("recommended_laptops", [])
        user_context = state.get("user_input", "")

        explanation_prompt = f"""
        The following laptops have been recommended based on the user's needs:

        {reccomended_laptops}

        Please provide a detailed explanation of why these laptops are suitable for the user.

        Here is the context about the user:
        {user_context}
        """

        explanation = llm.invoke(explanation_prompt)

        return Command(
            update={"final_response": explanation.content},
            goto="send_reply",
        )

    def send_reply(state: SalesAgentState) -> dict:
        """Output the final response."""
        print("\n" + "=" * 80)
        print("AGENT RESPONSE:")
        print("=" * 80)
        print(state["final_response"])
        print("=" * 80 + "\n")
        return {}

    workflow = StateGraph(SalesAgentState)
    workflow.add_node("read_user_prompt", read_user_prompt)
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("get_filtered_laptops", get_filtered_laptops)
    workflow.add_node("inform_user_no_laptops", inform_user_no_laptops)
    workflow.add_node("get_recommended_laptops", get_recommended_laptops)
    workflow.add_node("explain_reccomandations", explain_reccomandations)
    workflow.add_node("send_reply", send_reply)

    workflow.add_edge(START, "read_user_prompt")
    workflow.add_edge("read_user_prompt", "classify_intent")
    workflow.add_edge("inform_user_no_laptops", "send_reply")
    workflow.add_edge("send_reply", END)

    memory = MemorySaver()

    walfred = workflow.compile(checkpointer=memory)
    return walfred
