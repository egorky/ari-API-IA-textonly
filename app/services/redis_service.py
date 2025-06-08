import redis
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)
redis_client = None

def get_redis_client():
    global redis_client
    if redis_client is None:
        try:
            logger.info(f"Initializing Redis client with host={settings.REDIS_HOST}, port={settings.REDIS_PORT}")
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=0, # Default DB
                decode_responses=True # Important for LangChain Redis Memory
            )
            # Test connection
            redis_client.ping()
            logger.info("Redis client connected successfully.")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            redis_client = None
        except Exception as e:
            logger.error(f"An unexpected error occurred while connecting to Redis: {e}")
            redis_client = None

    return redis_client

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    logger.info("Attempting standalone Redis client test...")
    try:
        # This test assumes Redis is running on localhost:6379 without a password
        # For this __main__ block, we directly instantiate instead of relying on global `settings`
        # which might not be configured if this script is run standalone.
        test_client = redis.Redis(host='localhost', port=6379, password=None, db=0, decode_responses=True)
        test_client.ping()
        logger.info("Successfully got Redis client for standalone test.")
        test_client.set("test_key_standalone", "test_value_standalone")
        logger.info(f"Get 'test_key_standalone': {test_client.get('test_key_standalone')}")
        test_client.delete("test_key_standalone") # Clean up
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Failed to connect to Redis for standalone test: {e}. Ensure Redis is running.")
    except Exception as e:
        logger.error(f"An error occurred during standalone Redis test: {e}")
