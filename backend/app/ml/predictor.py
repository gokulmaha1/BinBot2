import os
import joblib
import numpy as np
import pandas as pd
from typing import Optional
from pathlib import Path

FEATURE_COLUMNS = [
    "ema_9", "ema_21", "ema_50", "ema_200",
    "rsi_14", "macd", "macd_signal", "macd_hist",
    "bb_upper", "bb_middle", "bb_lower", "bb_width",
    "atr_14", "stoch_k", "stoch_d",
    "supertrend_upper", "supertrend_lower",
    "vwap", "obv", "sma_20", "sma_50",
    "volume", "price_change", "volume_ratio",
]


class MLPredictor:
    def __init__(self, model_path: str = "models"):
        self.model_path = Path(model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.scaler = None

    def load_model(self, symbol: str = "default") -> bool:
        model_file = self.model_path / f"xgboost_{symbol}.json"
        scaler_file = self.model_path / f"scaler_{symbol}.pkl"
        if model_file.exists() and scaler_file.exists():
            import xgboost as xgb
            self.model = xgb.XGBClassifier()
            self.model.load_model(str(model_file))
            self.scaler = joblib.load(str(scaler_file))
            return True
        return False

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame(index=df.index)
        for col in FEATURE_COLUMNS:
            if col in df.columns:
                features[col] = df[col]
            else:
                features[col] = 0

        features["supertrend"] = df["supertrend"].map({"BUY": 1, "SELL": -1}).fillna(0) if "supertrend" in df.columns else 0
        features["price_change"] = df["close"].pct_change().fillna(0)
        features["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean() if "volume" in df.columns else 1
        features["volume_ratio"] = features["volume_ratio"].fillna(1)

        return features

    def predict(self, df: pd.DataFrame, symbol: str = "default") -> Optional[dict]:
        if self.model is None:
            if not self.load_model(symbol):
                return None

        features = self.prepare_features(df)
        last_row = features.iloc[[-1]]

        if last_row.isnull().any().any():
            last_row = last_row.fillna(0)

        try:
            scaled = self.scaler.transform(last_row)
            prediction = self.model.predict(scaled)[0]
            probabilities = self.model.predict_proba(scaled)[0]
            confidence = float(max(probabilities))

            return {
                "prediction": "BUY" if prediction == 1 else "SELL" if prediction == -1 else "HOLD",
                "confidence": confidence,
                "prob_buy": float(probabilities[1]) if len(probabilities) > 1 else 0,
                "prob_sell": float(probabilities[0]) if len(probabilities) > 0 else 0,
            }
        except Exception:
            return None

    def train_model(self, df: pd.DataFrame, symbol: str = "default") -> dict:
        import xgboost as xgb
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, precision_score, recall_score

        features = self.prepare_features(df)

        future_return = df["close"].shift(-10) / df["close"] - 1
        labels = pd.Series(0, index=df.index)
        labels[future_return > 0.005] = 1
        labels[future_return < -0.005] = -1

        valid = features.dropna()
        labels = labels[valid.index]

        if len(valid) < 100:
            return {"error": "Insufficient training data"}

        X_train, X_test, y_train, y_test = train_test_split(valid, labels, test_size=0.2, shuffle=False)

        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric="mlogloss",
        )

        self.model.fit(X_train_scaled, y_train)

        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
        recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)

        model_file = self.model_path / f"xgboost_{symbol}.json"
        scaler_file = self.model_path / f"scaler_{symbol}.pkl"
        self.model.save_model(str(model_file))
        joblib.dump(self.scaler, str(scaler_file))

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
        }


ml_predictor = MLPredictor()
