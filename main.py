import asyncio
import uvicorn
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    async_scoped_session,
)
from fastapi import FastAPI
from contextlib import contextmanager

app = FastAPI()

engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
session_factory = async_sessionmaker(
    engine, autoflush=False, autocommit=False, expire_on_commit=False
)
scoped_session_factory = async_scoped_session(
    session_factory, scopefunc=asyncio.current_task
)

# my idea: to create a custom context manager that is going to get session/connection (transaction) from a pool ({event: transaction}) by a event loop id.
connections = {}


@contextmanager
def get_current_session():
    current_task = asyncio.current_task()
    try:
        session = connections[hash(current_task)]
        yield session
    except KeyError:
        raise Exception("Session not found")


async def get_first_data():
    with get_current_session() as session:
        res = await session.execute(text("SELECT 1"))
        return res.scalar_one()


async def get_second_data():
    with get_current_session() as session:
        res = await session.execute(text("SELECT 2"))
        return res.scalar_one()


@app.get("/")
async def root():
    connections[hash(asyncio.current_task())] = scoped_session_factory()
    print(connections)

    res1 = await get_first_data()
    res2 = await get_second_data()
    print(res1, res2)

    del connections[hash(asyncio.current_task())]
    print(connections)

    # so, as you can see, this apploatch works as it's needed. Middleware unfortunatelly runs in a different event in event loop.
    # Another possible approatch -> to a context manager that doens't save anything based on session, but that just get current session but now with context manager!!! so, context manager in this case is a bad thing to use as it closes everything at the end!!!

    return {"message": "Hello World"}


if __name__ == "__main__":
    uvicorn.run(app)
