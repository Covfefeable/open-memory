from celery import shared_task
import time

@shared_task(ignore_result=False)
def process_message(message):
    time.sleep(5)  # Simulate long processing
    return f"Processed: {message}"
