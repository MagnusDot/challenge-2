from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from api.routers import aggregated_transactions, results, fraud_tools
from api.utils.data_loader import set_dataset_folder, get_dataset_folder

app = FastAPI(
    title="Reply Challenge API",
    description="API agrégée pour l'analyse de transactions avec toutes les données associées",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(aggregated_transactions.router)
app.include_router(results.router)
app.include_router(fraud_tools.router)

@app.get("/", include_in_schema=False)
async def root():

    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check():

    return {
        "status": "healthy",
        "version": "1.0.0",
        "message": "Reply Challenge API is running"
    }

@app.get("/stats")
async def get_global_stats():

    from api.utils.data_loader import (
        load_users,
        load_transactions,
        load_locations,
        load_sms,
        load_emails
    )

    try:
        return {
            "users": len(load_users()),
            "transactions": len(load_transactions()),
            "locations": len(load_locations()),
            "sms_messages": len(load_sms()),
            "emails": len(load_emails()),
            "current_dataset": get_dataset_folder(),
            "description": "API v2.0 - Endpoint unique /transactions/{id} pour données agrégées"
        }
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading data from dataset '{get_dataset_folder()}': {str(e)}"
        )

@app.get("/dataset/current")
async def get_current_dataset():

    from api.utils.data_loader import PROJECT_ROOT, get_dataset_dir

    dataset_folder = get_dataset_folder()
    dataset_dir = get_dataset_dir()

    exists = dataset_dir.exists()
    required_file = dataset_dir / "transactions_dataset.json"
    required_file_exists = required_file.exists()

    return {
        "dataset_folder": dataset_folder,
        "status": "active",
        "dataset_path": str(dataset_dir),
        "project_root": str(PROJECT_ROOT),
        "exists": exists,
        "required_file_exists": required_file_exists,
        "available_datasets": [
            d.name for d in (PROJECT_ROOT / "dataset").iterdir() 
            if d.is_dir() and (d / "transactions_dataset.json").exists()
        ] if (PROJECT_ROOT / "dataset").exists() else []
    }

@app.post("/dataset/reload")
async def reload_data():
    """Recharge toutes les données depuis les fichiers (vide le cache)."""
    from api.utils.data_loader import clear_cache, load_transactions, load_users, load_locations, load_sms, load_emails
    
    try:
        # Vider le cache
        clear_cache()
        
        # Recharger les données pour vérifier
        transactions = load_transactions()
        users = load_users()
        locations = load_locations()
        sms_messages = load_sms()
        emails = load_emails()
        
        return {
            "status": "success",
            "message": "Données rechargées avec succès",
            "cache_cleared": True,
            "data_loaded": {
                "transactions": len(transactions),
                "users": len(users),
                "locations": len(locations),
                "sms_messages": len(sms_messages),
                "emails": len(emails),
                "dataset": get_dataset_folder()
            }
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error reloading data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error reloading data: {str(e)}"
        )

@app.post("/dataset/{folder_name}")
async def switch_dataset(
    folder_name: str = Path(
        ...,
        description="Nom du dossier dataset à activer",
        example="public 2"
    )
):

    from api.utils.data_loader import PROJECT_ROOT

    try:
        old_folder = get_dataset_folder()
        set_dataset_folder(folder_name)

        from api.utils.data_loader import (
            load_transactions,
            load_users
        )

        transactions = load_transactions()
        users = load_users()

        return {
            "status": "success",
            "message": f"Dataset changé vers '{folder_name}'",
            "dataset_folder": folder_name,
            "previous_dataset": old_folder,
            "cache_cleared": True,
            "verification": {
                "transactions_loaded": len(transactions),
                "users_loaded": len(users),
                "dataset_path": str(PROJECT_ROOT / "dataset" / folder_name)
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error switching dataset: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error switching dataset: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )