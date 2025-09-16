import datetime
from confluent_kafka import Producer
from conf import settings
import json
from core.logging_config import get_logger

logger = get_logger(__name__)

def get_kafka_producer():
    return Producer({
        'bootstrap.servers': settings.KAFKA_BROKER_URL,
        'client.id': 'agent-api-producer',
    })

def send_to_kafka(topic: str, data: dict, producer=None):
    if not settings.KAFKA_ENABLED:
        logger.info("Kafka disabled — skipping message send.")
        return

    if producer is None:
        producer = get_kafka_producer()

    try:
        payload = json.dumps(data)
        producer.produce(topic, value=payload.encode('utf-8'), callback=delivery_report)
        producer.flush()
    except Exception as e:
        logger.exception(f"Error sending message to Kafka: {e}")

def test_producer():
    """Método para probar el envío de mensajes"""
    producer = get_kafka_producer()
    test_data = {
        "job_type": "test",
        "message": "Este es un mensaje de prueba",
        "timestamp": str(datetime.now())
    }
    send_to_kafka(settings.KAFKA_AGENT_TOPIC, test_data, producer)
    logger.info("Mensaje de prueba enviado a Kafka")

def delivery_report(err, msg):
    if err is not None:
        logger.error(f"Delivery failed for message: {err}")
    else:
        logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}]")