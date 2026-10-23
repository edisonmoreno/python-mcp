import os
from pathlib import Path

import streamlit as st
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

CERTIFICATE_PATH = str(Path(__file__).parent.parent / "global-bundle.pem")


def _build_conn_info() -> str:
    return make_conninfo(
        host="database-1.c25yk2iiiq52.us-east-1.rds.amazonaws.com",
        port=5432,
        dbname="postgres",
        user="postgres",
        password="HiOGxl0T3IHsNjnYjoUY",
        sslmode="verify-full",
        sslrootcert=CERTIFICATE_PATH,
    )


@st.cache_resource
def get_pool() -> ConnectionPool:
    pool = ConnectionPool(
        _build_conn_info(),
        min_size=1,
        max_size=5,
        open=False,
        kwargs={"row_factory": dict_row, "connect_timeout": 10},
    )
    pool.open()
    pool.wait(timeout=15)
    return pool
