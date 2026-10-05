import os

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


def get_conninfo() -> dict:
    return {
        "host": os.environ.get("DB_HOST"),
        "port": 5432,
        "dbname": os.environ.get("DB_NAME"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_ADMIN_PASSWORD"),
        "connect_timeout": 5,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db")
def db():
    try:
        with psycopg.connect(**get_conninfo()) as conn:
            row = conn.execute("SELECT version()").fetchone()
        return {"version": row[0]}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"detail": "Base de datos no disponible", "error": type(exc).__name__},
        )
