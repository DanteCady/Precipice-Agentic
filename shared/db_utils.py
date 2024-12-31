import psycopg2
from psycopg2.extras import RealDictCursor
import time
import logging

def get_db_connection(max_retries=5, retry_delay=5):
    """
    Establish a connection to the PostgreSQL database with retry logic.
    """
    retries = 0
    while retries < max_retries:
        try:
            return psycopg2.connect(
                dbname="boss_db",
                user="boss",
                password="boss_password",
                host="postgres",
                port=5432
            )
        except psycopg2.OperationalError as e:
            retries += 1
            if retries == max_retries:
                raise Exception(f"Failed to connect to database after {max_retries} attempts: {e}")
            logging.warning(f"Database connection attempt {retries} failed. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

def init_db():
    """
    Initialize the database schema with retry logic.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            tasks JSONB NOT NULL,
            status VARCHAR(50) DEFAULT 'in_progress',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
    finally:
        cursor.close()
        conn.close()
