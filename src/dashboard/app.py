import streamlit as st
import polars as pl
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from typing import Optional

from src.data.nba_data import RaptorsDataManager
from src.models.predictor import RaptorsPredictor
from src.utils.config import Config
from src.utils.cache import RedisCache

# Initialize configuration
config = Config()
cache = RedisCache()


# Cache data loading functions
@st.cache_data(ttl=3600)
def load_team_games(_data_manager: RaptorsDataManager, season: Optional[str] = None) -> Optional[pl.DataFrame]:
    """Load team games with caching"""
    return _data_manager.get_team_games(season)


@st.cache_data(ttl=3600)
def load_player_stats(_data_manager: RaptorsDataManager, season: Optional[str] = None) -> Optional[pl.DataFrame]:
    """Load player stats with caching"""
    return _data_manager.get_player_stats(season)


def create_team_stats_chart(df: pl.DataFrame, season: str = None) -> go.Figure:
    """Create an interactive team statistics chart"""
    if df is None:
        return None

    colors = config.chart_colors

    if season:
        df = df.filter(pl.col("SEASON") == season)

    # Prepare data once
    dates = df["GAME_DATE"].to_numpy()
    points = df["PTS"].to_numpy()
    moving_avg = df["PTS"].rolling_mean(window_size=5).to_numpy()

    fig = go.Figure()

    # Add points line
    fig.add_trace(go.Scatter(
        x=dates,
        y=points,
        name="Points",
        line=dict(color=colors["primary"], width=2),
        mode="lines+markers"
    ))

    # Add moving average
    fig.add_trace(go.Scatter(
        x=dates,
        y=moving_avg,
        name="5-Game Average",
        line=dict(color=colors["secondary"], width=2, dash="dash"),
        mode="lines"
    ))

    title = "Raptors Scoring Trend"
    if season:
        title += f" ({season})"

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Points",
        template="plotly_white",
        hovermode="x unified"
    )

    return fig


def create_win_loss_pie_chart(games_df: pl.DataFrame) -> go.Figure:
    """Create a pie chart for win-loss ratio"""
    if games_df is None:
        return None

    win_loss_counts = games_df.group_by("WL").count()

    fig = go.Figure(data=[go.Pie(labels=win_loss_counts["WL"], values=win_loss_counts["count"])])
    fig.update_layout(title="Win-Loss Ratio")

    return fig


def create_shooting_efficiency_heatmap(games_df: pl.DataFrame) -> go.Figure:
    """Create a heatmap for shooting efficiency"""
    if games_df is None:
        return None

    heatmap_data = games_df.select(["GAME_DATE", "FG_PCT", "FG3_PCT"]).to_pandas()

    fig = px.imshow(
        heatmap_data[["FG_PCT", "FG3_PCT"]].T,
        labels=dict(x="Game", y="Metric", color="Percentage"),
        x=heatmap_data["GAME_DATE"],
        y=["FG%", "3P%"],
        aspect="auto"
    )
    fig.update_layout(title="Shooting Efficiency Heatmap")

    return fig


def create_player_performance_radar(player_stats: pl.DataFrame, player_name: str) -> Optional[go.Figure]:
    """Create a radar chart for player performance"""
    player_data = player_stats.filter(pl.col("PLAYER_NAME") == player_name)

    if player_data.is_empty():
        return None

    # Calculate average metrics
    avg_metrics = (player_data
    .group_by("PLAYER_NAME")
    .agg([
        pl.col("PTS").mean().round(1).alias("AVG_PTS"),
        pl.col("REB").mean().round(1).alias("AVG_REB"),
        pl.col("AST").mean().round(1).alias("AVG_AST"),
        pl.col("FG_PCT").mean().round(3).alias("FG_PCT"),
        pl.col("STL").mean().round(1).alias("AVG_STL"),
        pl.col("BLK").mean().round(1).alias("AVG_BLK")
    ])
    )

    metrics = {
        "AVG_PTS": "Points",
        "AVG_REB": "Rebounds",
        "AVG_AST": "Assists",
        "FG_PCT": "FG%",
        "AVG_STL": "Steals",
        "AVG_BLK": "Blocks"
    }

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[avg_metrics[metric][0] for metric in metrics.keys()],
        theta=list(metrics.values()),
        fill='toself',
        name=player_name
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max([avg_metrics[metric][0] for metric in metrics.keys()])]
            )),
        showlegend=True,
        title=f"{player_name} Performance Radar"
    )

    return fig


def display_live_game(data_manager: RaptorsDataManager):
    """Display live game information if available"""
    try:
        live_game = data_manager.get_live_game_stats()

        if live_game is not None:
            game = live_game.row(0)

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
    except Exception as e:
        st.error(f"Error displaying live game: {str(e)}")


def display_player_stats(data_manager: RaptorsDataManager, season: str = None):
    """Display player statistics"""
    try:
        player_stats = load_player_stats(data_manager, season)

        if player_stats is not None:
            recent_stats = (player_stats
                            .lazy()
                            .group_by(["SEASON", "PLAYER_NAME"])
                            .agg([
                pl.col("PTS").mean().round(1).alias("AVG_PTS"),
                pl.col("REB").mean().round(1).alias("AVG_REB"),
                pl.col("AST").mean().round(1).alias("AVG_AST"),
                pl.col("FG_PCT").mean().round(3).alias("FG_PCT"),
                pl.col("PTS").count().alias("GAMES_PLAYED")
            ])
                            .sort(["SEASON", "AVG_PTS"], descending=[True, True])
                            .collect()
                            )

            st.dataframe(
                recent_stats,
                use_container_width=True,
                hide_index=True
            )
    except Exception as e:
        st.error(f"Error displaying player stats: {str(e)}")


def display_cache_stats():
    """Display cache performance metrics"""
    stats = cache.get_stats()
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Cache Hit Rate", stats['hit_rate'])
    with col2:
        st.metric("API Calls", stats['api_calls'])
    with col3:
        st.metric("Cache Size", stats['memory_cache_size'])


def main():
    st.set_page_config(
        page_title="Toronto Raptors Analytics Dashboard",
        page_icon="🏀",
        layout="wide",
    )

    # Initialize managers
    data_manager = RaptorsDataManager()
    predictor = RaptorsPredictor()

    # Header
    st.title("Toronto Raptors Analytics Dashboard")

    # Sidebar controls
    with st.sidebar:
        st.title("Dashboard Controls")

        # Season selector
        season_options = ["2024-25", "All Seasons", "2023-24"]
        selected_season = st.selectbox(
            "Select Season",
            options=season_options,
            index=0  # Default to "2024-25"
        )

        season = None if selected_season == "All Seasons" else selected_season

        auto_refresh = st.checkbox("Auto-refresh data", value=True)
        refresh_rate = st.slider(
            "Refresh rate (seconds)",
            min_value=10,
            max_value=300,
            value=config.refresh_rate
        )

        # Add cache control
        if st.button("Clear Cache"):
            data_manager.clear_cache()
            st.cache_data.clear()
            st.success("Cache cleared!")

        # Display cache stats
        display_cache_stats()

    # Main content using tabs
    tab1, tab2, tab3 = st.tabs(["Live Game", "Team Stats", "Player Stats"])

    with tab1:
        st.subheader("Live Game Status")
        display_live_game(data_manager)

        # Prediction section
        if st.button("Generate Next Game Prediction"):
            with st.spinner("Training prediction model..."):
                try:
                    # Get only the current season's games
                    games_df = load_team_games(data_manager, "2024-25")

                    if games_df is not None and len(games_df) >= 10:
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
                    else:
                        st.warning("Need at least 10 games in the current season for prediction")
                except Exception as e:
                    st.error(f"Error generating prediction: {str(e)}")

    with tab2:
        st.subheader("Team Performance")

        # Load data with progress indicator
        with st.spinner("Loading team stats..."):
            games_df = load_team_games(data_manager, season)

        if games_df is not None:
            # Create and display team stats chart
            fig = create_team_stats_chart(games_df, season)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            # Display recent game results
            st.subheader("Recent Games")
            recent_games = (games_df
                            .lazy()
                            .head(5)
                            .select([
                "GAME_DATE",
                "SEASON",
                "MATCHUP",
                "WL",
                "PTS",
                "FG_PCT",
                "FG3_PCT"
            ])
                            .collect()
                            )
            if not recent_games.is_empty():
                st.dataframe(
                    recent_games,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No recent games to display.")

            # Add Win-Loss Pie Chart
            st.subheader("Win-Loss Ratio")
            pie_chart = create_win_loss_pie_chart(games_df)
            if pie_chart:
                st.plotly_chart(pie_chart, use_container_width=True)

            # Add Shooting Efficiency Heatmap
            st.subheader("Shooting Efficiency")
            heatmap = create_shooting_efficiency_heatmap(games_df)
            if heatmap:
                st.plotly_chart(heatmap, use_container_width=True)

    with tab3:
        st.subheader("Player Statistics")

        # Load player stats
        player_stats = load_player_stats(data_manager, season)

        if player_stats is not None:
            display_player_stats(data_manager, season)

            # Add Player Performance Radar Chart
            player_name = st.selectbox("Select Player", player_stats["PLAYER_NAME"].unique())
            radar_chart = create_player_performance_radar(player_stats, player_name)
            if radar_chart:
                st.plotly_chart(radar_chart, use_container_width=True)
        else:
            st.info("No player stats available.")

    # Auto-refresh logic
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()


if __name__ == "__main__":
    main()
