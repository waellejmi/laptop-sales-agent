from agent import build_graph

walfred = build_graph(provider="groq")
config = {"configurable": {"thread_id": "test_session_1"}}


def test_agent(user_input: str):
    initial_state = {
        "user_input": user_input,
        "classification": None,
        "filtered_laptops": None,
        "game_specific_filters": None,
        "game_system_requirements": None,
        "recommended_laptops": None,
        "final_response": None,
        "messages": [],
    }

    result = walfred.invoke(initial_state, config)
    return result


def test_agent_with_streaming(user_input: str):
    initial_state = {
        "user_input": user_input,
        "classification": None,
        "game_system_requirements": None,
        "game_specific_filters": None,
        "filtered_laptops": None,
        "recommended_laptops": None,
        "final_response": None,
        "messages": [],
    }

    print(f"\n{'=' * 80}")
    print(f"USER INPUT: {user_input}")
    print(f"{'=' * 80}\n")

    for event in walfred.stream(initial_state, config):
        node_name = list(event.keys())[0]
        node_state = event[node_name]

        if not node_state:
            print(f"\n--- NODE: {node_name} (no state update) ---")
            continue

        print(f"\n--- NODE: {node_name} ---")

        classification = node_state.get("classification")
        if classification:
            print(f"Classification: {classification}")

        game_system_requirements = node_state.get("game_system_requirements")
        if game_system_requirements is not None:
            if isinstance(game_system_requirements, dict):
                print(f"Game System Requirements: {game_system_requirements} ")
            game_specific_filters = node_state.get("game_specific_filters")
            if isinstance(game_specific_filters, dict):
                print(f"Game Specific Filters: {game_specific_filters} ")

        filtered = node_state.get("filtered_laptops")
        if filtered is not None:
            if isinstance(filtered, list):
                print(f"Filtered Laptops: {len(filtered)} found")
            else:
                print(f"Filtered Laptops: {filtered}")

        recommended = node_state.get("recommended_laptops")
        if recommended:
            print(f"Recommendations: {len(recommended)}")
            for i, laptop in enumerate(recommended, 1):
                print(
                    f"  {i}. {laptop.get('model_name')} - €{laptop.get('price_euro')}"
                )

        final_response = node_state.get("final_response")
        if final_response:
            print(f"\nFinal Response: {final_response[:200]}...")

    print(f"\n{'=' * 80}\n")
    return walfred.get_state(config)


if __name__ == "__main__":
    print("# TEST 1: Gaming Laptop")
    test_agent_with_streaming(
        "I need the best gaming laptop under 3000 euros. I need to play the latest games in 4K smoothly"
    )

    print("\n # TEST 2: Apple Fanboy")
    test_agent(
        "I really like apple eco system, and i would love adding a new laptop, I only do basic web surfing and nothing heavy. What is the best i can get for 1500 euros?"
    )

    print("\n # TEST 3: Exact Model")
    test_agent(
        "I'm searching exactly for this laptop Lenovo IdeaPad Gaming 3 82K201UEIN. Do you have it in your store?"
    )
    print("\n # TEST 4: Very Specific Student Needs")
    test_agent(
        "I am going to uni this year and I need a lapoptop for taking notes and doing assignments. Money is most important factor for me. I need best price to performance ratio. My budget is 800 euros, i can go a bit higher like 100 extra euro max"
    )
    print("\n # TEST 5: MultiLangual Test")
    test_agent(
        "أريد لابتوب للألعاب"
    )  # "orid laptop lel al3ab" in arabic means i want a laptop for gaming in case you dont have an arabic font in your system (my nvim does not support it and I am lazy to add it)
    print("# TEST 6: Specific Game + filters ")
    test_agent_with_streaming(
        " There is a game called 'factorio', i have a budget of 500 euros which pc should i get? btw i really want asus ah i heard they are very relaible "
    )
