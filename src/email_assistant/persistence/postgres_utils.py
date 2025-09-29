import os
from typing import Dict

from psycopg import AsyncConnection

from email_assistant.logger import logger


def get_connection_args() -> Dict:
    """
    Constructs a dictionary of connection arguments required to connect to a PostgresSQL
    database. The function retrieves environment variable values and formats them into
    a dictionary.

    :return: Dict A dictionary containing the connection arguments to connect to a PostgresSQL
        database.
    """
    return {
        "host": os.getenv("POSTGRES_HOST"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "sslmode": os.getenv("POSTGRES_SSL_MODE"),
        "autocommit": True,
        "sslrootcert": os.getenv("POSTGRES_SSL_ROOT_CERT", "/app/config/dynamic_cert.crt"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "dbname": os.getenv("POSTGRES_DB"),
    }


def get_db_uri() -> str:
    """
    Constructs the Database URI string for connecting to a PostgresSQL database server.
    """
    return (
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@"
        f"{os.getenv('POSTGRES_HOST')}:{int(os.getenv('POSTGRES_PORT', 5432))}/{os.getenv('POSTGRES_DB')}"
        f"?sslmode={os.getenv('POSTGRES_SSL_MODE','disable')}&sslrootcert={os.getenv('POSTGRES_SSL_ROOT_CERT','/app/config/dynamic_cert.crt')}"  # noqa E501
    )


async def check_connection(conn: AsyncConnection) -> bool:
    """
    Performs a check on the given database connection to ensure it is functional.

    :param conn:AsyncConnection Asynchronous database connection object to be checked.
    :return: Boolean value whether the connection check was successful.
    """
    try:
        logger.debug("Connection check")
        await conn.execute("SELECT 1")
    except Exception as e:
        logger.warning(f"Connection check failed: {e}")
        return False
    return True
