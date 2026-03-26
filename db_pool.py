import os
import time
from dotenv import load_dotenv
from mysql.connector import pooling
from mysql.connector.errors import PoolError

load_dotenv()


def _pool_size_from_env(default=60):
    raw_value = os.getenv("DB_POOL_SIZE", str(default)).strip()
    try:
        value = int(raw_value)
        return max(1, value)
    except (TypeError, ValueError):
        return default


shared_connection_pool = pooling.MySQLConnectionPool(
    pool_name="shared_main_pool",
    pool_size=_pool_size_from_env(),
    pool_reset_session=True,
    host=os.getenv("server_ip"),
    user="ubuntu",
    database="load_consolidation",
    password=os.getenv("server_password"),
)


def get_connection_with_retry(retries=3, delay=0.5):
    for attempt in range(retries):
        try:
            return shared_connection_pool.get_connection()
        except PoolError:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise PoolError("All DB connections are busy")
