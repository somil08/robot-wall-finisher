from fastapi import FastAPI
from app.api.routers import router
from app.logging_conf import LoggingMiddleware
from app.db.database import engine
from app.db import models

app = FastAPI(title="Robot Wall Finisher API")

# Logging
app.add_middleware(LoggingMiddleware)

# Create tables
models.metadata.create_all(bind=engine)

# Include routes
app.include_router(router)

@app.get("/")
def root():
    return {"message": "Robot Wall Finisher backend is running 🚀"}
