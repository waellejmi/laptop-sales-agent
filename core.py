from filter import filter_laptops
from scoring import compute_scores, get_weights

filter = filter_laptops(
    model_name="Asus",
    price_euro=2000,
    resolution_type="4K",
)


weights = get_weights("gaming", user_emphasis=["price"])
ranked = compute_scores(filter, weights)
print(ranked)
