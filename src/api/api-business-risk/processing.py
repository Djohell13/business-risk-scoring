import pandas as pd
import numpy as np
import xgboost as xgb
import json
import os
import boto3

# --- 1. CHARGEMENT DES CONFIGURATIONS ---
# On récupère la liste des colonnes depuis le Secret
FEATURES = json.loads(os.getenv("MODEL_FEATURES", "[]"))

def load_from_s3(file_name):
    """Charge un dictionnaire JSON depuis S3"""
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )
        
        # Le nom du bucket vient de ton secret, ou on le force ici s'il est mal configuré
        bucket = os.getenv("AWS_BUCKET_NAME", "projet-economie")
        
        # LA CLÉ RÉELLE (ne doit pas contenir le nom du bucket au début)
        key = f"models/{file_name}" 
        
        print(f"🔍 Tentative S3 : Bucket={bucket} | Key={key}")
        
        response = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"❌ ÉCHEC S3 sur {file_name} : {e}")
        return {}

# Chargement (les variables seront enfin remplies !)
DEP_RISK_MAP = load_from_s3("mapping_dep_risk.json")
APE_SECTION_MAP = load_from_s3("mapping_ape_section.json")

# --- 2. CALCULS ---
def get_sigma(model):
    try:
        config = json.loads(model.save_config())
        def find_key(obj, key):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == key: return v
                    res = find_key(v, key)
                    if res is not None: return res
            elif isinstance(obj, list):
                for item in obj:
                    res = find_key(item, key)
                    if res is not None: return res
            return None
        scale = find_key(config, 'aft_loss_distribution_scale')
        return float(scale) if scale else 0.8
    except:
        return 0.8

def calculate_survival_risk(mu, horizon, s):
    z = (np.log(horizon) - mu) / s
    z = np.clip(z, -50, 50)
    return round((1 / (1 + np.exp(-z))) * 100, 2)

def map_statut_expert(p2):
    if p2 > 20: return '🔴 CRITIQUE'
    if p2 > 10: return '🟠 VIGILANCE'
    if p2 > 5:  return '🟡 OBSERVATION'
    return '🟢 SAIN'

# --- 3. PRÉPARATION DES DONNÉES ---
def prepare_input(data):
    # Création du DF avec les colonnes du Secret
    df = pd.DataFrame(0.0, index=[0], columns=FEATURES)
    
    # Remplissage des variables
    # On utilise .loc[0, col] pour être sûr de ne pas créer de nouvelles colonnes
    if 'age_au_diagnostic' in df.columns:
        df.loc[0, 'age_au_diagnostic'] = float(data.get('age_estime', 0))
    
    if 'Tranche_effectif_num' in df.columns:
        df.loc[0, 'Tranche_effectif_num'] = float(data.get('Tranche_effectif_num', 0))
    
    if 'is_ess' in df.columns:
        df.loc[0, 'is_ess'] = int(data.get('is_ess', 0))
    
    # Risque départemental
    code_dep = str(data.get('code_departement', '')).strip().upper()
    if 'risque_departemental' in df.columns:
        df.loc[0, 'risque_departemental'] = float(DEP_RISK_MAP.get(code_dep, 0.05))
    
    # Mapping APE
    code_ape = str(data.get('code_ape', '')).zfill(2)
    section_name = APE_SECTION_MAP.get(code_ape)
    if section_name:
        col_ape = f"APE_{section_name}"
        if col_ape in df.columns:
            df.loc[0, col_ape] = 1.0
        elif 'APE_Autres_Secteurs' in df.columns:
            df.loc[0, 'APE_Autres_Secteurs'] = 1.0
            
    # Mapping CJ
    cj_prefix = str(data.get('categorie_juridique', ''))[:4]
    col_cj = f"CJ_{cj_prefix}"
    if col_cj in df.columns:
        df.loc[0, col_cj] = 1.0

    # LOG DE DEBUG (Visible dans les logs HF)
    print(f"DEBUG: Age envoyé={data.get('age_estime')} | Valeur dans DF={df['age_au_diagnostic'].iloc[0]}")
    
    return xgb.DMatrix(df)