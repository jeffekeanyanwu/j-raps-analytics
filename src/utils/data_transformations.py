import polars as pl
from typing import List, Tuple


def prepare_ml_features(df: pl.DataFrame) -> Tuple[pl.DataFrame, pl.Series]:
    """
    Prepare features for ML model using Polars efficient operations
    """
    # Create features DataFrame
    features = (df
                .with_columns([
        pl.col("PTS").rolling_mean(window_size=5).alias("pts_ma_5"),
        pl.col("FG_PCT").rolling_mean(window_size=5).alias("fg_pct_ma_5"),
        pl.col("FG3_PCT").rolling_mean(window_size=5).alias("fg3_pct_ma_5"),
    ])
                .drop_nulls()
                )

    # Separate target variable
    target = features.get_column("PTS")
    features = features.drop("PTS")

    return features, target


def create_game_summary(df: pl.DataFrame) -> pl.DataFrame:
    """
    Create a summary of game statistics using Polars
    """
    return (df
            .group_by("GAME_DATE")
            .agg([
        pl.col("PTS").mean().alias("avg_points"),
        pl.col("FG_PCT").mean().alias("avg_fg_pct"),
        pl.col("FG3_PCT").mean().alias("avg_fg3_pct"),
        pl.col("PTS").count().alias("games_played")
    ])
            .sort("GAME_DATE", descending=True)
            )
