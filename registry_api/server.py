import csv
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException

REGISTRY_DIR = Path(__file__).resolve().parent.parent / "registry"
API_KEY = os.environ.get("REGISTRY_API_KEY", "dev-key")

app = FastAPI(title="Mock Transfer Agent Registry API")


def _rows(name):
    with open(REGISTRY_DIR / name, newline="") as f:
        return list(csv.DictReader(f))


def check_key(x_api_key: str = Header(default="")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid API key")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/investors", dependencies=[Depends(check_key)])
def investors():
    return _rows("investors.csv")


@app.get("/holdings", dependencies=[Depends(check_key)])
def holdings():
    return _rows("holdings.csv")


@app.get("/fund", dependencies=[Depends(check_key)])
def fund():
    return _rows("fund.csv")
