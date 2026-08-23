import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test")
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public';"))
            tables = [row[0] for row in res.fetchall()]
            print("Tables in datacube_bot_test:", tables)
    except Exception as e:
        print("Error connecting to test db:", e)

    engine2 = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot")
    try:
        async with engine2.connect() as conn:
            res = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public';"))
            tables = [row[0] for row in res.fetchall()]
            print("Tables in datacube_bot:", tables)
    except Exception as e:
        print("Error connecting to bot db:", e)

asyncio.run(check())
