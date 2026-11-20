def route_order(order: dict) -> str:
    


assert route_order({"status": "CANCELLED", "order_type": "electronics"}) == "cancellations"
assert route_order({"order_type": "Electronics"}) == "tech_support"
assert route_order({"order_type": "clothing", "status": "pending"}) == "returns"
assert route_order({"order_type": "FOOD"}) == "fulfillment"
assert route_order({"order_type": "furniture"}) == "general"
assert route_order({}) == "general"
assert route_order({"order_type": None}) == "general"
assert route_order({"status": None, "order_type": "food"}) == "fulfillment"

print("all pass")