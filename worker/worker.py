import json
import logging
import os
import time

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from pymongo import MongoClient
from pymongo.errors import PyMongoError

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

TOPIC_NAME = "orders"
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

# 1. הגדרת חיבור ל-MongoDB
logger.info(f"Connecting to MongoDB at {MONGO_URI}...")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["shop_db"]
collection = db["orders"]
# Enforces one document per order_id, even if two workers race.
# Partial: legacy orders saved before order_id existed are ignored by the index.
collection.create_index(
    "order_id",
    unique=True,
    partialFilterExpression={"order_id": {"$type": "string"}},
)


def deserialize_message(value):
    if value is None:
        return None
    try:
        return json.loads(value.decode("utf-8"))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode message: {e}")
        return None


logger.info(f"Connecting to Kafka at {KAFKA_BROKER}...")
consumer = None

while consumer is None:
    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=[KAFKA_BROKER],
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            group_id="orders",
            value_deserializer=deserialize_message,
        )
        logger.info("Successfully connected to Kafka!")
    except NoBrokersAvailable:
        logger.warning("Kafka is not ready yet, retrying in 5 seconds...")
        time.sleep(5)

logger.info(f"Listening to Kafka Topic: '{TOPIC_NAME}'...")

try:
    for message in consumer:
        data = message.value

        if data is None or "order_id" not in data:
            # Undecodable or missing order_id message: skip it permanently so it isn't re-read forever
            consumer.commit()
            continue
        logger.info(f"Received from Kafka: {data}")

        # Simulated background work (payment, stock, email...)
        logger.info(f"Processing order {data['order_id']}...")
        time.sleep(5)

        # Retry until updated; commit the offset only after success
        # (at-least-once delivery), so a Mongo failure never drops an order.
        while True:
            try:
                # Only pending orders change, so reprocessing a message is a no-op
                result = collection.update_one(
                    {"order_id": data["order_id"], "status": "pending"},
                    {"$set": {"status": "completed"}},
                )
                logger.info(
                    f"Order {data['order_id']} completed (updated={result.modified_count})"
                )
                consumer.commit()
                break
            except PyMongoError as e:
                logger.error(f"Failed to save document to MongoDB, retrying in 5s: {e}")
                time.sleep(5)

except KeyboardInterrupt:
    logger.info("Shutting down worker...")
finally:
    if consumer is not None:
        consumer.close()
    mongo_client.close()
    logger.info("Connections closed safely.")
