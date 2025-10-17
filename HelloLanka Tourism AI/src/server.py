from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .contracts import TripRequest
from .graph_pipeline import run_graph

app = FastAPI(title="HelloLanka Tourism AI", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/plan")
async def plan_trip(req: TripRequest):
    try:
        result = run_graph(req.model_dump(), trace=False)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


