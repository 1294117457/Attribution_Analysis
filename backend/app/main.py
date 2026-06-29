from fastapi import FastAPI
from app.api.router import api_router
from app.api.database.connection import engine
from app.database.models.base import Base

app=FastAPI(
  title="智能金融数据归因分析平台",
  version="1.0.0",
)

app.include_router(api_router)

@app.on_event("startup")
def on_startup()
  Base.metadata.create_all(bind=engine)
  