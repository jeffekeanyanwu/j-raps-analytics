import polars as pl
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
from pathlib import Path

from src.utils.config import Config


class RaptorsPredictor:
    def __init__(self):
        self.config = Config()
        self.model = RandomForestRegressor(
            n_estimators=100,
            random_state=self.config.get('ml', 'model', 'training', 'random_state', default=42)
        )
        self.scaler = StandardScaler()

        # Create models directory if it doesn't exist
        model_dir = Path(self.config.model_path)
        model_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = model_dir / "raptors_predictor.joblib"

    def prepare_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """Prepare features for prediction using Polars"""
        window_size = 5  # Use a fixed window size for simplicity

        # Create rolling averages for each feature
        features_df = (df
                       .with_columns([
            pl.col("PTS").rolling_mean(window_size).alias("pts_ma_5"),
            pl.col("FG_PCT").rolling_mean(window_size).alias("fg_pct_ma_5"),
            pl.col("FG3_PCT").rolling_mean(window_size).alias("fg3_pct_ma_5"),
            pl.col("REB").rolling_mean(window_size).alias("reb_ma_5"),
            pl.col("AST").rolling_mean(window_size).alias("ast_ma_5")
        ])
                       .drop_nulls()
                       )

        return features_df

    def train(self, df: pl.DataFrame):
        """Train the prediction model"""
        features_df = self.prepare_features(df)

        # Prepare features and target
        feature_cols = ["pts_ma_5", "fg_pct_ma_5", "fg3_pct_ma_5", "reb_ma_5", "ast_ma_5"]
        X = features_df.select(feature_cols).to_numpy()
        y = df.get_column("PTS").tail(len(X)).to_numpy()

        # Split and scale
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.config.get('ml', 'model', 'training', 'test_size', default=0.2),
            random_state=self.config.get('ml', 'model', 'training', 'random_state', default=42)
        )

        X_train_scaled = self.scaler.fit_transform(X_train)

        # Train model
        self.model.fit(X_train_scaled, y_train)

        # Save model
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump((self.model, self.scaler), self.model_path)

        # Return test score
        X_test_scaled = self.scaler.transform(X_test)
        return self.model.score(X_test_scaled, y_test)

    def predict(self, features_df: pl.DataFrame) -> float:
        """Make predictions for next game"""
        if not self.model_path.exists():
            raise ValueError("Model not trained yet!")

        feature_cols = ["pts_ma_5", "fg_pct_ma_5", "fg3_pct_ma_5", "reb_ma_5", "ast_ma_5"]
        features = features_df.select(feature_cols).to_numpy()

        self.model, self.scaler = joblib.load(self.model_path)
        features_scaled = self.scaler.transform(features)
        return self.model.predict(features_scaled)[-1]  # Return latest prediction
