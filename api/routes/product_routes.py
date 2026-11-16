from datetime import UTC, datetime

from bson import ObjectId
from db import db
from flask import Blueprint, jsonify, request
from models.product import ProductCreate, ProductResponse

product_blueprint = Blueprint("products", __name__)


@product_blueprint.route("/products", methods=["POST"])
def create_product():
    data = ProductCreate(**request.get_json()).model_dump()
    data["created_at"] = datetime.now(tz=UTC)

    result = db.products.insert_one(data)

    inserted_doc = db.products.find_one({"_id": result.inserted_id})
    return (
        ProductResponse.model_validate(inserted_doc).model_dump_json(),
        201,
        {"Content-Type": "application/json"},
    )


@product_blueprint.route("/products", methods=["GET"])
def get_products():
    docs = list(db.products.find())
    response_data = [ProductResponse(**doc).model_dump(by_alias=True) for doc in docs]
    return jsonify(response_data), 200


@product_blueprint.route("/products/<string:product_id>", methods=["GET"])
def get_product(product_id):
    if not ObjectId.is_valid(product_id):
        return jsonify({"error": "Malformed Hexadecimal ID"}), 400

    doc = db.products.find_one({"_id": ObjectId(product_id)})
    if not doc:
        return jsonify({"error": "Product not found"}), 404

    return (
        ProductResponse(**doc).model_dump_json(),
        200,
        {"Content-Type": "application/json"},
    )
