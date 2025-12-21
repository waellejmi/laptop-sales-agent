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
from sys_req_lookup_tool import GameNotFound, get_system_requirements

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
    sort_by_gpu_tier: Optional[bool] = False
    price_euro: Optional[float] = None


class GameSpecification(BaseModel):
    ram: Optional[int] = None
    gpu: Optional[str] = None


class UserRequestClassification(BaseModel):
    usage_profile: Literal["gaming", "student", "basic", "workstation"]
    user_emphasis: Optional[
        list[Literal["cpu_tier", "gpu_tier", "ram", "ssd_present", "price"]]
    ] = None
    filters: Optional[LaptopSpecification] = None
    specific_game: Optional[str] = None
    gibberish: Optional[bool] = False


class SalesAgentState(TypedDict):
    user_input: str

    classification: dict[str, Any] | None

    game_specific_filters: dict[str, Any] | None
    game_system_requirements: dict[str, Any] | None

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
    ) -> Command[
        Literal[
            "get_filtered_laptops",
            "get_recommended_laptops",
            "get_game_requirements",
            "inform_user_gibberish",
        ]
    ]:
        """Use LLM to parse user prompt to get his usage profile, his emphasis and hard filters."""

        structured_llm = llm.with_structured_output(UserRequestClassification)

        classification_prompt = f"""
        Your are AI Laptop Sales Assistant.
        Analyze this customer message and classify it:

        User Message: {state["user_input"]}

        Provide:
        1. usage_profile: One of ["gaming", "student", "basic", "workstation"]
        2. user_emphasis: List of emphasized features from ["cpu_tier", "gpu_tier", "ram", "ssd_present", "price"], or null
        3. filters: Dictionary of specific requirements mentioned or null if none specified
        4. specific_game: If the user mentions a specific game title, extract it. 
        5. gibberish: set it to True, if user talking out of laptops context or random typing

        Only include filters that are explicitly mentioned by the user.
        """

        classification = structured_llm.invoke(classification_prompt)

        if classification.gibberish:
            goto = "inform_user_gibberish"
        elif classification.specific_game:
            goto = "get_game_requirements"

        elif classification.filters:
            goto = "get_filtered_laptops"
        else:
            goto = "get_recommended_laptops"

        return Command(
            update={"classification": classification.model_dump()}, goto=goto
        )

    def get_game_requirements(
        state: SalesAgentState,
    ) -> Command[Literal["get_filtered_laptops"]]:
        classification = state.get("classification", {})
        game_name = classification.get("specific_game", "")
        try:
            recc_game_requirements = get_system_requirements(game_name)
            structured_llm = llm.with_structured_output(GameSpecification)

            mapping_prompt = f"""
                Given the following recommended system requirements for the game {recc_game_requirements["game_name"]}:

                GPU: {recc_game_requirements["gpu"]}
                RAM: {recc_game_requirements["ram"]}
                
                Our dataset includes:
                GPUs: GTX 1650, RTX 2050, RTX 3050, RTX 3050 Ti, RTX 3060, RTX 3070, RTX 3070 Ti, RTX 3080, RTX 3080 Ti

                Extract and map these requirements to the following laptop specification format:
                - Only extract Intel CPUs and Nvidia (RTX/GTX) GPUs. If the requirement is not Intel or Nvidia, set the value to None.
                - For RTX and GTX GPUs, use the format: RTX 3060, GTX 1660, etc.
                - If the game needs specific hardware not in our dataset, choose the closest possible match for example (RTX 2070 -> RTX 3050)
                - If the game requires hardware worse than our minimum spec laptops, set the value to our minimum spec hardware.

            """
            game_specific_filters = structured_llm.invoke(mapping_prompt)
            return Command(
                update={
                    "game_system_requirements": recc_game_requirements,
                    "game_specific_filters": game_specific_filters.model_dump(),
                },
                goto="get_filtered_laptops",
            )
        except GameNotFound as e:
            return Command(
                update={
                    "final_response": f"{str(e)}",
                },
                goto="inform_user_no_laptops",
            )

    def get_filtered_laptops(
        state: SalesAgentState,
    ) -> Command[Literal["get_recommended_laptops", "inform_user_no_laptops"]]:
        """Filter laptops based on user criteria."""
        classification = state.get("classification", {})
        game_requirements = state.get("game_specific_filters", {})
        filters = classification.get("filters") or {}

        if isinstance(game_requirements, dict) and game_requirements.get("ram"):
            filters["ram"] = game_requirements["ram"]
        if isinstance(game_requirements, dict) and game_requirements.get("gpu"):
            filters["gpu"] = game_requirements["gpu"]
            filters["sort_by_gpu_tier"] = True
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
        game_requirements = state.get("game_system_requirements", {})

        if isinstance(game_requirements, dict) and game_requirements.get("game_name"):
            explanation_prompt = f"""
            The following laptops have been recommended based on the user's need to play on reccomanded settings this game: {game_requirements["game_name"]}

            {reccomended_laptops}

            Please provide a detailed explanation of why these laptops are suitable for the user.

            Here is the context about the user:
            {user_context}

            Here is the context about the game  recommended system requirements:
            f"GPU: {game_requirements["gpu"]}\n"
            f"RAM: {game_requirements["ram"]}\n\n"

            """
        else:
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

    def inform_user_no_laptops(state: SalesAgentState) -> dict:
        """Inform the user that no laptops matched their criteria."""
        return {
            "final_response": (
                "Unfortunately, no laptops match your specified criteria in our database."
                "Please consider adjusting your requirements."
            )
        }

    def inform_user_gibberish(state: SalesAgentState) -> dict:
        """Inform the user he is talking out of context."""
        return {
            "final_response": (
                "Unfortunately, we did not understand your request. Please stay on topic of laptops."
                "I am here to help you find a Laptop specific to your needs."
            )
        }

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
    workflow.add_node("get_game_requirements", get_game_requirements)
    workflow.add_node("get_filtered_laptops", get_filtered_laptops)
    workflow.add_node("get_recommended_laptops", get_recommended_laptops)
    workflow.add_node("explain_reccomandations", explain_reccomandations)
    workflow.add_node("inform_user_no_laptops", inform_user_no_laptops)
    workflow.add_node("inform_user_gibberish", inform_user_gibberish)
    workflow.add_node("send_reply", send_reply)

    workflow.add_edge(START, "read_user_prompt")
    workflow.add_edge("read_user_prompt", "classify_intent")
    workflow.add_edge("inform_user_no_laptops", "send_reply")
    workflow.add_edge("inform_user_gibberish", "send_reply")
    workflow.add_edge("send_reply", END)

    memory = MemorySaver()

    walfred = workflow.compile(checkpointer=memory)
    return walfred
