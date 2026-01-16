from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter(prefix="/api", tags=["results"])

RESULTS_DIR = Path("/app/scripts/results")


@router.get("/results")
async def list_results():
    if not RESULTS_DIR.exists():
        return []
    
    json_files = [
        f.name
        for f in RESULTS_DIR.iterdir()
        if f.is_file() and f.suffix == ".json" and "summary" not in f.name.lower()
    ]
    return sorted(json_files)


@router.get("/results/{filename}")
async def get_result_file(filename: str):
    file_path = RESULTS_DIR / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.get("/transactions")
async def get_all_transactions():
    from api.utils.data_loader import load_transactions
    
    try:
        transactions = load_transactions()
        return [t.model_dump() for t in transactions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading transactions: {str(e)}")
