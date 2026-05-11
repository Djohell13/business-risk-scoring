import os
import json
import numpy as np
import xgboost as xgb
import pandas as pd
import mlflow.xgboost
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

# On importe les fonctions et la constante FEATURES depuis processing
from processing import prepare_input, calculate_survival_risk, map_statut_expert, get_sigma, FEATURES

# --- 1. CONFIGURATION MLFLOW ---
load_dotenv()
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))

RUN_ID = "674d07aab0b0493a838310da47c71a95"
MODEL_URI = f"runs:/{RUN_ID}/model"

# --- 2. INITIALISATION DE L'API ---
app = FastAPI(
    title="Business Risk API",
    description="API de prédiction du risque de fermeture des entreprises via modèle AFT.",
    version="3.6.0"
)

# Variables globales
model = None
SIGMA = None

@app.on_event("startup")
async def load_model():
    global model, SIGMA
    try:
        print(f"🚀 Connexion à MLflow : {os.getenv('MLFLOW_TRACKING_URI')}")
        loaded_model = mlflow.xgboost.load_model(MODEL_URI)
        
        if isinstance(loaded_model, xgb.Booster):
            model = loaded_model
        else:
            model = loaded_model.get_booster()
            
        SIGMA = get_sigma(model)
        print(f"✅ Modèle chargé avec succès (Sigma: {round(SIGMA, 4)})")
    except Exception as e:
        print(f"❌ Erreur lors du chargement du modèle : {e}")

# --- 3. ROUTES ---

@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/docs")

@app.get("/health", tags=["Système"])
def health():
    return {
        "status": "online",
        "model_loaded": model is not None,
        "run_id": RUN_ID,
        "features_synced": len(FEATURES) > 0
    }

@app.post("/predict", tags=["Prédiction"])
async def predict(
    data: dict = Body(..., example={
        "age_estime": 0.5,
        "Tranche_effectif_num": 0,
        "code_departement": "75",
        "code_ape": "56",
        "categorie_juridique": "5499",
        "is_ess": 0
    })
):
    """
    Simule le risque de fermeture d'une entreprise à 1, 2 et 3 ans.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Modèle non disponible")

    try:
        # 1. Préparation des données (Utilise le mapping S3)
        dmatrix = prepare_input(data)
        
        # 2. Inférence (Score MU)
        mu = float(model.predict(dmatrix)[0])
        
        # 3. Calcul des probabilités avec le Sigma extrait du modèle
        p1 = calculate_survival_risk(mu, 1, SIGMA)
        p2 = calculate_survival_risk(mu, 2, SIGMA)
        p3 = calculate_survival_risk(mu, 3, SIGMA)
        
        return {
            "diagnostic": {
                "profil_global": map_statut_expert(p2),
                "indice_confiance_mu": round(mu, 4)
            },
            "probabilites_fermeture": {
                "1_an": f"{p1}%",
                "2_ans": f"{p2}%",
                "3_ans": f"{p3}%"
            },
            "entrees_recues": {
                "age_saisi": data.get("age_estime"),
                "division_ape": data.get("code_ape"),
                "departement": data.get("code_departement")
            },
            "debug_internal": {
                "features_count": len(FEATURES),
                "first_feature": FEATURES[0] if FEATURES else "None"
            },
            "metadonnees": {
                "run_id": RUN_ID,
                "sigma_utilise": round(SIGMA, 6),
                "api_version": "3.6.0"
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la prédiction : {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)