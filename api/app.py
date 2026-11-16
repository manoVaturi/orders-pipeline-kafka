import json
import os
import uuid
from datetime import UTC, datetime
from typing import Annotated

from bson import ObjectId
from db import db
from flask import Flask, jsonify, render_template, request
from kafka import KafkaProducer
from kafka.errors import KafkaError
from models import OrderCreate, OrderItem, ProductModel
from pydantic import BeforeValidator, ValidationError
from routes.order_routes import order_blueprint
from routes.product_routes import product_blueprint

app = Flask(__name__)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

TOPIC_NAME = "orders"

products_collection = db["products"]

PyObjectId = Annotated[str, BeforeValidator(str)]

app.register_blueprint(product_blueprint, url_prefix="/api")
app.register_blueprint(order_blueprint, url_prefix="/api")


@app.errorhandler(ValidationError)
def handle_pydantic_validation_errors(err):
    return jsonify(
        {
            "error": "Unprocessable JSON Schema Payload",
            "details": err.errors(include_url=False, include_context=False),
        }
    ), 422


@app.route("/product", methods=["POST"])
def create_product():
    product = ProductModel(**request.get_json())

    product_dict = product.model_dump(by_alias=True, exclude_none=True)
    result = products_collection.insert_one(product_dict)

    return jsonify({"id": str(result.inserted_id)}), 201


# 4. Read Documents (GET)
@app.route("/products", methods=["GET"])
def get_products():
    products = []
    for doc in products_collection.find():
        product = ProductModel(**doc)
        products.append(product.model_dump())
    return jsonify(products), 200


@app.route("/checkout", methods=["POST"])
def checkout():
    payload_data = request.get_json(silent=True)
    if not isinstance(payload_data, dict):
        return jsonify({"error": "Missing or invalid JSON payload"}), 400

    payload = OrderCreate(**payload_data)

    items = []
    total_amount = 0.0
    for item in payload.items:
        if not ObjectId.is_valid(item.product_id):
            return jsonify({"error": f"Invalid product ID: {item.product_id}"}), 400
        product = products_collection.find_one({"_id": ObjectId(item.product_id)})
        if not product:
            return jsonify({"error": f"Product {item.product_id} not found"}), 404

        items.append(
            OrderItem(
                product_id=str(product["_id"]),
                product_name=product["name"],
                quantity=item.quantity,
                price_at_purchase=float(product["price"]),
            ).model_dump()
        )
        total_amount += float(product["price"]) * item.quantity

    # 1. Save the order as "pending"; the worker completes it later
    order = {
        "order_id": str(uuid.uuid4()),
        "user_id": payload.user_id,
        "items": items,
        "total_amount": round(total_amount, 2),
        "status": "pending",
        "created_at": datetime.now(tz=UTC),
    }
    db.orders.insert_one(order)

    # 2. Queue only the id; the order itself is already in MongoDB
    try:
        # Wait for the broker ack so a failed delivery is reported to the client
        producer.send(TOPIC_NAME, {"order_id": order["order_id"]}).get(timeout=10)
    except KafkaError as e:
        db.orders.update_one(
            {"order_id": order["order_id"]}, {"$set": {"status": "failed"}}
        )
        return jsonify({"error": "Failed to queue order", "details": str(e)}), 503

    return jsonify(
        {
            "status": "success",
            "message": "Order accepted and is being processed",
            "order_id": order["order_id"],
        }
    ), 202


@app.route("/")
def index():
    products = []
    for doc in products_collection.find():
        product = ProductModel(**doc)
        products.append(product.model_dump())

    return render_template("index.html", products=products)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
