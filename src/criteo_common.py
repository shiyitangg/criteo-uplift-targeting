"""Shared loader: DuckDB reads the CSV straight from disk (fast, low memory).
Falls back to SQLite via pandas if DuckDB is not installed (slow on the full 14M rows)."""
import pandas as pd

def connect(csv_path):
    try:
        import duckdb
        con = duckdb.connect()
        con.execute(f"CREATE TABLE criteo AS SELECT * FROM read_csv_auto('{csv_path}')")
        run = lambda q: con.execute(q).df()
        return run, "DuckDB", con
    except ImportError:
        import sqlite3
        con = sqlite3.connect(":memory:")
        pd.read_csv(csv_path).to_sql("criteo", con, index=False)
        return (lambda q: pd.read_sql_query(q, con)), "SQLite", con

def sample_rows(run, engine, n):
    if engine == "DuckDB":
        return run(f"SELECT * FROM criteo USING SAMPLE {int(n)} ROWS")
    return run(f"SELECT * FROM criteo ORDER BY RANDOM() LIMIT {int(n)}")
