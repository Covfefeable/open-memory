from celery import shared_task
import time

@shared_task
def process_message(message):
    """
    Example background task that processes a message.
    In a real application, this might involve complex processing,
    external API calls, or database operations.
    """
    # Simulate processing time
    time.sleep(5)
    return f"Processed message: {message}"