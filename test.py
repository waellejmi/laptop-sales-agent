from agent import build_graph


def test_agent(user_input: str):
    walfred = build_graph(provider="groq")

    config = {"configurable": {"thread_id": "test_session_1"}}

    initial_state = {
        "user_input": user_input,
        "classification": None,
        "filtered_laptops": None,
        "recommended_laptops": None,
        "final_response": None,
        "messages": [],
    }

    result = walfred.invoke(initial_state, config)
    return result


if __name__ == "__main__":
    print("TEST 1: Basic gaming laptop")
    test_agent("I need a gaming laptop under 2000 euros")

    print("\nTEST 2: Specific requirements")
    test_agent("I want an Asus laptop with 4K display for gaming, budget is 2000 euros")

    print("\nTEST 3: Student laptop")
    test_agent(
        "I'm a student, need something for programming and web browsing, around 800 euros"
    )
    print("\nTEST 4: No matches")
    test_agent("I need a laptop with 128GB RAM and RTX 4090 under 500 euros")
