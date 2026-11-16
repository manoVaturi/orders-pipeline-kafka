"""Seed the products collection.

Run from the project root:  make seed
or:                         cd api && python bootstrap/db-init.py
Safe to re-run: products are upserted by sku, so no duplicates are created.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

# Allow `from db import db` when run as a script (sys.path[0] is bootstrap/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import db
from pymongo import ASCENDING, UpdateOne

PRODUCTS = [
    ("MUG-001", "Ceramic Mug", 9.99),
    ("MUG-002", "Travel Mug", 14.50),
    ("TSH-001", "Cotton T-Shirt", 19.90),
    ("TSH-002", "Graphic T-Shirt", 24.90),
    ("HOD-001", "Hoodie", 49.00),
    ("CAP-001", "Baseball Cap", 15.00),
    ("BAG-001", "Canvas Tote Bag", 12.75),
    ("BAG-002", "Laptop Backpack", 59.99),
    ("BTL-001", "Steel Water Bottle", 18.50),
    ("NTB-001", "Notebook A5", 6.25),
    ("PEN-001", "Gel Pen Set (5)", 7.40),
    ("STK-001", "Sticker Pack", 3.99),
    ("MSE-001", "Wireless Mouse", 22.99),
    ("KBD-001", "Mechanical Keyboard", 89.90),
    ("HDP-001", "Over-Ear Headphones", 79.00),
    ("CHG-001", "USB-C Charger 65W", 29.99),
    ("CBL-001", "USB-C Cable 1m", 8.99),
    ("LMP-001", "LED Desk Lamp", 34.50),
    ("PAD-001", "Mouse Pad XL", 11.99),
    ("PWR-001", "Power Bank 10000mAh", 27.00),
]


def seed_products() -> int:
    """Upsert by sku; existing products are left untouched."""
    products = db["products"]
    products.create_index([("sku", ASCENDING)], unique=True)

    now = datetime.now(tz=UTC)
    ops = [
        UpdateOne(
            {"sku": sku},
            {
                "$setOnInsert": {
                    "sku": sku,
                    "name": name,
                    "price": price,
                    "created_at": now,
                }
            },
            upsert=True,
        )
        for sku, name, price in PRODUCTS
    ]
    result = products.bulk_write(ops)
    print(
        f"Inserted {result.upserted_count} new products, {len(PRODUCTS) - result.upserted_count} already existed."
    )
    return products.count_documents({})


if __name__ == "__main__":
    print(f"Total products in DB: {seed_products()}")
