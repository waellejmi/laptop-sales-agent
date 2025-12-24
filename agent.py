import json
import logging
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

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import AnyUrl
from pydantic import BaseModel

from filter import filter_laptops
from scoring import compute_scores, get_weights
from sys_req_lookup_tool import (
    GameNotFound,
    local_lookup,
)

load_dotenv()


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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


class SalesAgent:
    def __init__(self, provider: str = "groq"):
        if provider == "groq":
            GROQ_API_KEY = os.getenv("GROQ_KEY")
            self.llm = ChatGroq(
                model="qwen/qwen3-32b", api_key=GROQ_API_KEY, temperature=0.5
            )
        elif provider == "huggingface":
            HF_TOKEN = os.getenv("HF_TOKEN")
            self.llm = ChatHuggingFace(
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
        self._game_db_path: Optional[str] = None
        self._laptop_db_path: Optional[str] = None
        self.server_params = StdioServerParameters(
            command="python", args=["mcp_server.py"]
        )

    # MCP SETup
    async def _get_resource_path_from_session(self, session, uri: str) -> str:
        result = await session.read_resource(AnyUrl(uri))
        raw_text = result.contents[0].text
        logger.info(f"Resource info for {uri}: {raw_text}")
        resource_info = json.loads(raw_text)
        return resource_info["path"]

    async def get_mcp_paths(self):
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                resources = await session.list_resources()
                logger.info("MCP CONNECTED")
                logger.info("Available MCP Resources:")
                for resource in resources.resources:
                    logger.info(f"  - {resource.name}: {resource.uri}")
                self._game_db_path = await self._get_resource_path_from_session(
                    session, "file:///data/games-system-requirements/game_db.csv"
                )
                self._laptop_db_path = await self._get_resource_path_from_session(
                    session, "file:///data/laptops_enhanced.csv"
                )

    async def online_lookup_mcp(self, game_name: str) -> dict:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                logger.info("Available MCP Tools:")
                for tool in tools.tools:
                    logger.info(f"  - {tool.name}: {tool.description}")

                result = await session.call_tool(
                    "online_lookup", arguments={"game_name": game_name}
                )
                return json.loads(result.content[0].text)

    # Agent logic and nodes
    def read_user_prompt(self, state: SalesAgentState) -> dict:
        # maybe i add read from a text file or live from a cli
        return {
            "messages": [
                HumanMessage(content=f"Processing User Input: {state['user_input']}")
            ]
        }

    def classify_intent(
        self,
        state: SalesAgentState,
    ) -> Command[
        Literal[
            "get_filtered_laptops",
            "get_recommended_laptops",
            "get_game_requirements",
            "inform_user_gibberish",
        ]
    ]:
        structured_llm = self.llm.with_structured_output(UserRequestClassification)

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

    async def get_game_requirements(
        self,
        state: SalesAgentState,
    ) -> Command[Literal["get_filtered_laptops", "inform_user_no_laptops"]]:
        classification = state.get("classification", {})
        game_name = classification.get("specific_game", "")
        try:
            try:
                # we first look online, because it faster than querying this 80K entry we have
                full_res = await self.online_lookup_mcp(game_name)

                if not full_res.get("success"):
                    raise GameNotFound("Online lookup failed")

                recc_game_requirements = full_res["data"]
            except GameNotFound:
                # if it fails we check the local db plus local db have only minimum requirments
                recc_game_requirements = local_lookup(
                    game_name, path=self._game_db_path
                )
            structured_llm = self.llm.with_structured_output(GameSpecification)

            mapping_prompt = f"""
                Given the following recommended system requirements for the game {recc_game_requirements["game_name"]}:

                GPU: {recc_game_requirements["gpu"]}
                RAM: {recc_game_requirements["ram"]}
                
                Our dataset includes:
                GPUs: GTX 1650, RTX 2050, RTX 3050, RTX 3050 Ti, RTX 3060, RTX 3070, RTX 3070 Ti, RTX 3080, RTX 3080 Ti

                Extract and map these requirements to the following laptop specification format:
                - Only extract Nvidia (RTX/GTX) GPUs. If the requirement is worse than out minimum GPU (GTX 1650 in this case), set the value to GTX 1650.
                - For RTX and GTX GPUs, use the format: RTX 3060, GTX 1660, etc.
                - If the game needs specific hardware not in our dataset, choose the closest possible match for example (RTX 2070 -> RTX 3050)
                - If the game requires hardware worse than our minimum spec laptops, set the value to our minimum spec hardware (GTX 1650).

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
        self,
        state: SalesAgentState,
    ) -> Command[Literal["get_recommended_laptops", "inform_user_no_laptops"]]:
        classification = state.get("classification", {})
        game_requirements = state.get("game_specific_filters", {})
        filters = classification.get("filters") or {}

        if isinstance(game_requirements, dict) and game_requirements.get("ram"):
            filters["ram"] = game_requirements["ram"]
        if isinstance(game_requirements, dict) and game_requirements.get("gpu"):
            filters["gpu"] = game_requirements["gpu"]
            filters["sort_by_gpu_tier"] = True
        try:
            # filtered_laptops_df = filter_laptops(**filters)
            filtered_laptops_df = filter_laptops(
                dataset_path=self._laptop_db_path, **filters
            )
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
        self,
        state: SalesAgentState,
    ) -> Command[Literal["explain_reccomandations"]]:
        classification = state.get("classification", {})
        usage_profile = classification.get("usage_profile", "basic")
        user_emphasis = classification.get("user_emphasis", [])
        filtered_laptops = state.get("filtered_laptops", list[dict])

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
        self,
        state: SalesAgentState,
    ) -> Command[Literal["send_reply"]]:
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
            GPU: {game_requirements["gpu"]}\n
            CPU: {game_requirements["cpu"]}\n
            RAM: {game_requirements["ram"]}\n

            """
        else:
            explanation_prompt = f"""
            The following laptops have been recommended based on the user's needs:

            {reccomended_laptops}

            Please provide a detailed explanation of why these laptops are suitable for the user.

            Here is the context about the user:
            {user_context}
            """

        explanation = self.llm.invoke(explanation_prompt)

        return Command(
            update={"final_response": explanation.content},
            goto="send_reply",
        )

    @staticmethod
    def inform_user_no_laptops(state: SalesAgentState) -> dict:
        return {
            "final_response": (
                "Unfortunately, no laptops match your specified criteria in our database."
                "Please consider adjusting your requirements."
            )
        }

    @staticmethod
    def inform_user_gibberish(state: SalesAgentState) -> dict:
        return {
            "final_response": (
                "Unfortunately, we did not understand your request. Please stay on topic of laptops."
                "I am here to help you find a Laptop specific to your needs."
            )
        }

    @staticmethod
    def send_reply(state: SalesAgentState) -> dict:
        print("\n" + "=" * 80)
        print("AGENT RESPONSE:")
        print("=" * 80)
        print(state["final_response"])
        print("=" * 80 + "\n")
        return {}


async def build_graph(provider: str = "groq"):
    agent = SalesAgent(provider)
    await agent.get_mcp_paths()

    workflow = StateGraph(SalesAgentState)
    workflow.add_node("read_user_prompt", agent.read_user_prompt)
    workflow.add_node("classify_intent", agent.classify_intent)
    workflow.add_node("get_game_requirements", agent.get_game_requirements)
    workflow.add_node("get_filtered_laptops", agent.get_filtered_laptops)
    workflow.add_node("get_recommended_laptops", agent.get_recommended_laptops)
    workflow.add_node("explain_reccomandations", agent.explain_reccomandations)
    workflow.add_node("inform_user_no_laptops", agent.inform_user_no_laptops)
    workflow.add_node("inform_user_gibberish", agent.inform_user_gibberish)
    workflow.add_node("send_reply", agent.send_reply)
    workflow.add_edge(START, "read_user_prompt")
    workflow.add_edge("read_user_prompt", "classify_intent")
    workflow.add_edge("inform_user_no_laptops", "send_reply")
    workflow.add_edge("inform_user_gibberish", "send_reply")
    workflow.add_edge("send_reply", END)

    memory = MemorySaver()

    graph = workflow.compile(checkpointer=memory)
    return graph
