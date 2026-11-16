from datetime import UTC, datetime

from bson import ObjectId
from db import db
from flask import Blueprint, jsonify, request
from models.order import OrderCreate, OrderItem, OrderResponse

order_blueprint = Blueprint("orders", __name__)


@order_blueprint.route("/orders", methods=["GET"])
@order_blueprint.route("/getAllBoughtItems", methods=["GET"])
def get_all_bought_items():
    user_id = request.args.get("user_id", "").strip()
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    orders = list(
        db.orders.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1)
    )
    items = [
        {
            **item,
            "order_id": order.get("order_id"),
            "status": order.get("status"),
            "created_at": order.get("created_at"),
        }
        for order in orders
        for item in order.get("items", [])
    ]
    return jsonify({"user_id": user_id, "orders": orders, "items": items}), 200


@order_blueprint.route("/orders", methods=["POST"])
def create_order():
    payload_data = request.get_json(silent=True)
    if not isinstance(payload_data, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400

    payload = OrderCreate(**payload_data)

    validated_items = []
    total_amount = 0.0

    for item in payload.items:
        if not ObjectId.is_valid(item.product_id):
            return jsonify(
                {"error": f"Invalid product ID string: {item.product_id}"}
            ), 400

        product = db.products.find_one({"_id": ObjectId(item.product_id)})
        if not product:
            return jsonify(
                {"error": f"Product {item.product_id} completely missing"}
            ), 404

        stock = product.get("stock")
        if stock is not None and stock < item.quantity:
            return jsonify(
                {"error": f"Insufficient stock for product: {product['name']}"}
            ), 400

        order_item = OrderItem(
            product_id=str(product["_id"]),
            product_name=product["name"],
            quantity=item.quantity,
            price_at_purchase=float(product["price"]),
        )
        validated_items.append(order_item.model_dump())
        total_amount += float(product["price"]) * item.quantity

    for item in payload.items:
        db.products.update_one(
            {"_id": ObjectId(item.product_id)}, {"$inc": {"stock": -item.quantity}}
        )

    order_doc = {
        "user_id": payload.user_id,
        "items": validated_items,
        "total_amount": total_amount,
        "status": "pending",
        "created_at": datetime.now(tz=UTC),
    }

    result = db.orders.insert_one(order_doc)
    inserted_order = db.orders.find_one({"_id": result.inserted_id})

    if inserted_order is None:
        return jsonify({"error": "Order could not be retrieved after creation"}), 500

    order_response = OrderResponse.model_validate(inserted_order)
    return (
        order_response.model_dump_json(),
        201,
        {"Content-Type": "application/json"},
    )
