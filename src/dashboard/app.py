import streamlit as st
import polars as pl
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

from src.data.nba_data import RaptorsDataManager
from src.models.predictor import RaptorsPredictor
from src.utils.config import Config

# Initialize configuration
config = Config()


def create_team_stats_chart(df: pl.DataFrame) -> go.Figure:
    """Create an interactive team statistics chart"""
    colors = config.chart_colors

    fig = go.Figure()

    # Add points line
    fig.add_trace(go.Scatter(
        x=df["GAME_DATE"].to_numpy(),
        y=df["PTS"].to_numpy(),
        name="Points",
        line=dict(color=colors["primary"], width=2),
        mode="lines+markers"
    ))

    # Add moving average
    fig.add_trace(go.Scatter(
        x=df["GAME_DATE"].to_numpy(),
        y=df["PTS"].rolling_mean(window_size=5).to_numpy(),
        name="5-Game Average",
        line=dict(color=colors["secondary"], width=2, dash="dash"),
        mode="lines"
    ))

    fig.update_layout(
        title="Raptors Scoring Trend",
        xaxis_title="Date",
        yaxis_title="Points",
        template="plotly_white",
        hovermode="x unified"
    )

    return fig


def display_live_game(data_manager: RaptorsDataManager):
    """Display live game information if available"""
    live_game = data_manager.get_live_game_stats()

    if live_game is not None:
        game = live_game.row(0)

        # Create columns for score display
        col1, col2, col3 = st.columns([2, 1, 2])

        with col1:
            st.subheader(game["homeTeam"])
            st.header(str(game["homeScore"]))

        with col2:
            st.subheader("VS")
            st.write(f"Q{game['period']}")
            st.write(game["gameClock"])

        with col3:
            st.subheader(game["awayTeam"])
            st.header(str(game["awayScore"]))
    else:
        st.info("No live game in progress")


def display_player_stats(data_manager: RaptorsDataManager):
    """Display player statistics"""
    player_stats = data_manager.get_player_stats()

    if player_stats is not None:
        # Get recent player averages
        recent_stats = (player_stats
                       .group_by("PLAYER_NAME")
                       .agg([
                           pl.col("PTS").mean().round(1).alias("AVG_PTS"),
                           pl.col("REB").mean().round(1).alias("AVG_REB"),
                           pl.col("AST").mean().round(1).alias("AVG_AST"),
                           pl.col("FG_PCT").mean().round(3).alias("FG_PCT")
                       ])
                       .sort("AVG_PTS", descending=True)
                       )

        st.dataframe(
            recent_stats,
            use_container_width=True,
            hide_index=True
        )


def main():
    st.set_page_config(
        page_title="Raptors Analytics Dashboard",
        page_icon="🏀",
        layout="wide",
    )

    # Initialize managers
    data_manager = RaptorsDataManager()
    predictor = RaptorsPredictor()

    # Header
    st.title("Toronto Raptors Analytics Dashboard")

    # Sidebar controls
    st.sidebar.title("Dashboard Controls")
    auto_refresh = st.sidebar.checkbox("Auto-refresh data", value=True)
    refresh_rate = st.sidebar.slider(
        "Refresh rate (seconds)",
        min_value=10,
        max_value=300,
        value=config.refresh_rate
    )

    # Main content
    tab1, tab2, tab3 = st.tabs(["Live Game", "Team Stats", "Player Stats"])

    with tab1:
        st.subheader("Live Game Status")
        display_live_game(data_manager)

        # Prediction section
        if st.button("Generate Next Game Prediction"):
            with st.spinner("Training prediction model..."):
                games_df = data_manager.get_team_games()
                features_df = predictor.prepare_features(games_df)

                if not predictor.model_path.exists():
                    score = predictor.train(games_df)
                    st.write(f"Model R² Score: {score:.3f}")

                prediction = predictor.predict(features_df)
                st.metric(
                    "Predicted Points Next Game",
                    f"{prediction:.1f}",
                    delta=f"{prediction - games_df['PTS'].mean():.1f} vs average"
                )

    with tab2:
        st.subheader("Team Performance")
        games_df = data_manager.get_team_games()

        # Create and display team stats chart
        fig = create_team_stats_chart(games_df)
        st.plotly_chart(fig, use_container_width=True)

        # Display recent game results
        st.subheader("Recent Games")
        recent_games = (games_df
                       .head(5)
                       .select([
                           "GAME_DATE",
                           "MATCHUP",
                           "WL",
                           "PTS",
                           "FG_PCT",
                           "FG3_PCT"
                       ])
                       )
        st.dataframe(
            recent_games,
            use_container_width=True,
            hide_index=True
        )

    with tab3:
        st.subheader("Player Statistics")
        display_player_stats(data_manager)

        # Auto-refresh logic
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()  # Updated from experimental_rerun


if __name__ == "__main__":
    main()
