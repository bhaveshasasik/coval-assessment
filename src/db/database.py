"""
SQLite database setup and connection management.
"""

import aiosqlite
from pathlib import Path

# Database file path
DB_PATH = Path(__file__).parent.parent.parent / "verifications.db"


async def init_db():
    """Initialize the database with required tables"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                id TEXT PRIMARY KEY,
                workflow_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                verdict TEXT NOT NULL,
                node_completion_rate REAL,
                critical_node_pass BOOLEAN,
                edge_accuracy REAL,
                valid_path_matched BOOLEAN,
                order_violation BOOLEAN,
                first_deviation_point REAL,
                low_confidence_count INTEGER,
                unauthorized_steps INTEGER,
                requires_human_review BOOLEAN,
                critical_violation_count INTEGER,
                total_violation_count INTEGER,
                actual_sequence TEXT,
                required_sequence TEXT,
                summary TEXT,
                workflow_json TEXT,
                transcript_json TEXT,
                results_json TEXT,
                metrics_json TEXT
            )
        """)
        await db.commit()


async def get_db_connection():
    """Get a database connection"""
    return aiosqlite.connect(DB_PATH)


def ensure_db_exists():
    """Ensure the database file and tables exist (synchronous)"""
    import asyncio

    asyncio.run(init_db())
