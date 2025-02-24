import os
from redis import Redis
from rq import Worker, Queue, Connection
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Redis connection
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_conn = Redis.from_url(redis_url)

if __name__ == '__main__':
    # Start the worker
    with Connection(redis_conn):
        worker = Worker([Queue('videos')])
        worker.work()
