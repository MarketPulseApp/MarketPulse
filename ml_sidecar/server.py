import logging
import os

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from feature_engineering import FeatureEngineer
from models import OHLCVPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MarketPulse ML Sidecar", version="0.1.0")
engineer = FeatureEngineer()

# Load the trained models globally
MODEL_PATH = "/opt/marketpulse/models/rf_baseline_model.joblib"
ANOMALY_MODEL_PATH = "/opt/marketpulse/models/anomaly_model.joblib"
model = None
anomaly_model = None

@app.on_event("startup")
def load_model():
    global model, anomaly_model
    try:
        if os.path.exists(MODEL_PATH):
            model = joblib.load(MODEL_PATH)
            logger.info(f"Successfully loaded model from {MODEL_PATH}")
        else:
            logger.warning(f"Model file not found at {MODEL_PATH}")
            
        if os.path.exists(ANOMALY_MODEL_PATH):
            anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
            logger.info(f"Successfully loaded anomaly model from {ANOMALY_MODEL_PATH}")
        else:
            logger.warning(f"Anomaly model file not found at {ANOMALY_MODEL_PATH}")
            
    except Exception as e:
        logger.error(f"Failed to load models: {e}")

@app.get("/health")
def health():
    """
    Health check endpoint for the ML sidecar.
    """
    return {"status": "ok", "service": "ml-sidecar", "model_loaded": model is not None, "anomaly_loaded": anomaly_model is not None}

@app.post("/features/generate")
async def generate_features(payload: OHLCVPayload) -> dict:
    """
    Endpoint to generate machine learning features from a batch of OHLCV data.
    """
    try:
        result = engineer.generate_features(payload.data)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/predict")
async def predict(payload: OHLCVPayload) -> dict:
    """
    Endpoint for making predictions using the loaded baseline model.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
        
    try:
        # 1. Engineer features
        features = engineer.generate_features(payload.data)
        
        # 2. Extract the exact feature columns required by the model
        feature_cols = [
            'open', 'high', 'low', 'close', 'volume',
            'rsi_14', 'macd', 'macd_signal', 'macd_diff',
            'bb_bbm', 'bb_bbh', 'bb_bbl', 'vwap', 'ema_9', 'ema_21',
            'put_call_ratio', 'macro_cpi', 'stocktwits_sentiment', 'congressional_buys',
            'insider_buys', 'insider_sells', 'reddit_sentiment', 'rss_sentiment'
        ]
        
        # Ensure all columns exist in the feature dictionary, default to 0 if missing
        row = []
        for col in feature_cols:
            val = features.get(col)
            row.append(float(val) if val is not None else 0.0)
            
        # 3. Create a DataFrame for the single row (model expects 2D array/DataFrame)
        df_input = pd.DataFrame([row], columns=feature_cols)
        
        # 4. Check for anomalies
        is_anomaly = False
        if anomaly_model:
            anomaly_pred = anomaly_model.predict(df_input)[0]
            is_anomaly = bool(anomaly_pred == -1)
            
        # 5. Predict probabilities (0 for down, 1 for up)
        probabilities = model.predict_proba(df_input)[0]
        confidence_down = probabilities[0]
        confidence_up = probabilities[1]
        
        signal = "HOLD"
        confidence = 0.0
        
        if is_anomaly:
            signal = "HOLD"
            confidence = 0.0
        elif confidence_up > 0.99:
            signal = "BUY"
            confidence = confidence_up
        elif confidence_down > 0.99:
            signal = "SELL"
            confidence = confidence_down
            
        return {
            "signal": signal,
            "confidence": float(confidence),
            "is_anomaly": bool(is_anomaly),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during prediction")

import subprocess


@app.post("/retrain")
async def retrain_model():
    """
    Endpoint to trigger a full retraining of the ML models using the latest data.
    """
    try:
        logger.info("Starting automated model retraining...")
        script_path = os.path.join(os.path.dirname(__file__), 'train_model.py')
        
        result = subprocess.run(['python', script_path], capture_output=True, text=True, check=True)
        logger.info(f"Retraining output: {result.stdout}")
        
        # Hot-reload the model globally
        load_model()
        
        return {"status": "success", "message": "Models retrained and hot-reloaded successfully"}
    except subprocess.CalledProcessError as e:
        logger.error(f"Retraining failed: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Retraining failed: {e.stderr}")
    except Exception as e:
        logger.error(f"Error during retraining: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during retraining")
