from fastapi import FastAPI
from pydantic import BaseModel
import os
import time
import random

app = FastAPI()

NODE_NAME = os.environ.get("NODE_NAME", "unknown-node")

class WorkRequest(BaseModel):
    payload: str

@app.get("/health")
def health():
    return {"status": "ok", "node": NODE_NAME}

@app.post("/work")
def do_work(req: WorkRequest):
    """
    Fake some processing:
    - random latency
    - return node name + echo payload
    """
    # simulate processing time
    time.sleep(random.uniform(0.01, 0.15))

    return {
        "node": NODE_NAME,
        "received": req.payload,
        "status": "processed"
    }

@app.get("/state")
def state():
    """
    Later we can add some fake internal state here.
    For now just return node name + timestamp.
    """
    return {
        "node": NODE_NAME,
        "timestamp": time.time()
    }
