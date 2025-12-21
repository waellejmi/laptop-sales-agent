from filter import filter_laptops
from scoring import compute_scores, get_weights

# This is basically what the agent is doing but just in automated process

filter = filter_laptops(
    # model_name="Asus",
    # price_euro=500,
    # resolution_type="4K",
    gpu="rx 5500",
    sort_by_gpu_tier=True,
)


weights = get_weights("gaming", user_emphasis=["price"])
ranked = compute_scores(filter, weights)
ranked = ranked.head(2)
print(ranked.to_dict(orient="records"))
