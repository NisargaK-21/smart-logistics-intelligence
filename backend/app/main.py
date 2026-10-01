from fastapi import FastAPI

app = FastAPI(
    title="Smart Logistics Intelligence API",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "Smart Logistics Intelligence API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }