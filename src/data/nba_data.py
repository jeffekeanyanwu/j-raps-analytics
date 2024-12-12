from nba_api.stats.static import teams
from nba_api.stats.endpoints import teamgamelog, commonteamroster
from nba_api.live.nba.endpoints import scoreboard
import polars as pl
from datetime import datetime
import time
from pathlib import Path

from src.utils.config import Config
from src.utils.cache import cache_decorator, RedisCache


class RaptorsDataManager:
    def __init__(self):
        self.config = Config()
        self.team_id = self.config.team_id
        self.api_delay = self.config.nba_delay

    def _rate_limit(self):
        """Implement rate limiting for API calls"""
        time.sleep(self.api_delay)

    @cache_decorator(expire_in=300)  # Cache for 5 minutes
    def get_team_games(self, season: str = None) -> pl.DataFrame:
        """Fetch team game logs for the specified season"""
        if season is None:
            season = self.config.default_season

        self._rate_limit()
        game_log = teamgamelog.TeamGameLog(
            team_id=self.team_id,
            season=season
        )

        # Convert to Polars and process
        df = pl.from_pandas(game_log.get_data_frames()[0])
        return (df
                .with_columns([
                    # Convert "APR 14, 2024" format to date
                    pl.col("GAME_DATE").str.strptime(pl.Date, "%b %d, %Y", strict=False),
                    pl.col("PTS").cast(pl.Int32),
                    pl.col("FG_PCT").cast(pl.Float32),
                    pl.col("FG3_PCT").cast(pl.Float32),
                    pl.col("REB").cast(pl.Int32),
                    pl.col("AST").cast(pl.Int32)
                ])
                .sort("GAME_DATE", descending=True)
                )

    @cache_decorator(expire_in=60)  # Cache for 1 minute
    def get_live_game_stats(self) -> pl.DataFrame:
        """Fetch live game stats if a game is in progress"""
        self._rate_limit()
        try:
            board = scoreboard.ScoreBoard()
            games = board.games.get_dict()

            # Find Raptors game
            raptors_game = None
            for game in games:
                if str(game['homeTeam']['teamId']) == self.team_id or \
                        str(game['awayTeam']['teamId']) == self.team_id:
                    raptors_game = game
                    break

            if raptors_game:
                # Convert to Polars DataFrame with specific columns
                return pl.DataFrame([{
                    'gameId': raptors_game['gameId'],
                    'homeTeam': raptors_game['homeTeam']['teamName'],
                    'awayTeam': raptors_game['awayTeam']['teamName'],
                    'homeScore': raptors_game['homeTeam']['score'],
                    'awayScore': raptors_game['awayTeam']['score'],
                    'period': raptors_game.get('period', 0),
                    'gameClock': raptors_game.get('gameClock', ''),
                    'gameStatus': raptors_game.get('gameStatus', 'Unknown')
                }])
            return None
        except Exception as e:
            print(f"Error fetching live game stats: {e}")
            return None

    @cache_decorator(expire_in=3600)  # Cache for 1 hour
    def get_player_stats(self, season: str = None) -> pl.DataFrame:
        """Fetch and process player stats for the current roster"""
        if season is None:
            season = self.config.default_season

        # Get current roster
        self._rate_limit()
        roster = commonteamroster.CommonTeamRoster(team_id=self.team_id)
        roster_df = pl.from_pandas(roster.get_data_frames()[0])

        # Create a mapping of player IDs to names
        player_names = dict(zip(roster_df["PLAYER_ID"], roster_df["PLAYER"]))

        # Fetch stats for each player
        player_stats = []
        for player_id in roster_df["PLAYER_ID"]:
            self._rate_limit()
            try:
                from nba_api.stats.endpoints import playergamelog
                player_log = playergamelog.PlayerGameLog(
                    player_id=str(player_id),
                    season=season
                )
                # Convert to Polars DataFrame
                df = player_log.get_data_frames()[0]
                if not df.empty:
                    stats = pl.from_pandas(df)
                    # Add player name to the stats
                    stats = stats.with_columns(
                        pl.lit(player_names[player_id]).alias("PLAYER_NAME")
                    )
                    player_stats.append(stats)
            except Exception as e:
                print(f"Error fetching stats for player {player_id}: {e}")
                continue

        if player_stats:
            try:
                # Concatenate all player stats
                combined_stats = pl.concat(player_stats)

                # Process and clean the data
                return (combined_stats
                        .with_columns([
                            # Handle date separately
                            pl.col("GAME_DATE").str.strptime(pl.Date, "%b %d, %Y", strict=False),
                            # Handle percentages
                            pl.col("FG_PCT").cast(pl.Float32),
                            pl.col("FG3_PCT").cast(pl.Float32),
                            pl.col("FT_PCT").cast(pl.Float32),
                            # Handle numeric columns
                            pl.col("PTS").cast(pl.Int32),
                            pl.col("REB").cast(pl.Int32),
                            pl.col("AST").cast(pl.Int32),
                            pl.col("STL").cast(pl.Int32),
                            pl.col("BLK").cast(pl.Int32),
                            pl.col("TOV").cast(pl.Int32),
                            pl.col("PF").cast(pl.Int32)
                        ])
                        .select([
                            "PLAYER_NAME",
                            "GAME_DATE",
                            "PTS",
                            "REB",
                            "AST",
                            "FG_PCT",
                            "STL",
                            "BLK",
                            "TOV"
                        ])
                        .sort(["PLAYER_NAME", "GAME_DATE"], descending=[False, True])
                        )

            except Exception as e:
                print(f"Error processing player stats: {e}")
                return None
        return None

    def clear_cache(self):
        """Clear the Redis cache"""
        cache = RedisCache()
        cache.redis.flushall()
