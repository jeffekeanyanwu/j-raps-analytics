from nba_api.stats.static import teams
from nba_api.stats.endpoints import teamgamelog, commonteamroster
from nba_api.live.nba.endpoints import scoreboard
import polars as pl
from datetime import datetime
import time
from pathlib import Path
import concurrent.futures
from typing import List, Optional

from src.utils.config import Config
from src.utils.cache import cache_decorator, RedisCache


class RaptorsDataManager:
    def __init__(self):
        self.config = Config()
        self.team_id = self.config.team_id
        self.api_delay = self.config.nba_delay
        self.seasons = ["2023-24", "2024-25"]
        self.cache = RedisCache()

    def _rate_limit(self):
        """Implement rate limiting for API calls"""
        time.sleep(self.api_delay)

    def _fetch_season_games_async(self, season: str) -> Optional[pl.DataFrame]:
        """Fetch games for a season asynchronously"""
        try:
            self._rate_limit()
            game_log = teamgamelog.TeamGameLog(
                team_id=self.team_id,
                season=season
            )

            df = pl.from_pandas(game_log.get_data_frames()[0])
            return (df.lazy()
                    .with_columns([
                pl.col("GAME_DATE").str.strptime(pl.Date, "%b %d, %Y", strict=False),
                pl.col("PTS").cast(pl.Int32),
                pl.col("FG_PCT").cast(pl.Float32),
                pl.col("FG3_PCT").cast(pl.Float32),
                pl.col("REB").cast(pl.Int32),
                pl.col("AST").cast(pl.Int32),
                pl.lit(season).alias("SEASON")
            ])
                    .sort("GAME_DATE", descending=True)
                    .collect()
                    )
        except Exception as e:
            print(f"Error fetching games for season {season}: {e}")
            return None

    @cache_decorator(expire_in=3600)  # Cache for 1 hour
    def get_team_games(self, season: str = None) -> pl.DataFrame:
        """Fetch team game logs for specified season(s)"""
        if season is None:
            # Fetch all seasons in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_to_season = {
                    executor.submit(self._fetch_season_games_async, s): s
                    for s in self.seasons
                }

                all_games = []
                for future in concurrent.futures.as_completed(future_to_season):
                    result = future.result()
                    if result is not None:
                        all_games.append(result)

            return pl.concat(all_games) if all_games else None

        return self._fetch_season_games_async(season)

    @cache_decorator(expire_in=60)  # Cache for 1 minute
    def get_live_game_stats(self) -> Optional[pl.DataFrame]:
        """Fetch live game stats if a game is in progress"""
        self._rate_limit()
        try:
            board = scoreboard.ScoreBoard()
            games = board.games.get_dict()

            # Find Raptors game using list comprehension
            raptors_game = next(
                (game for game in games
                 if str(game['homeTeam']['teamId']) == self.team_id
                 or str(game['awayTeam']['teamId']) == self.team_id),
                None
            )

            if raptors_game:
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

    def _fetch_player_stats_async(self, player_id: str, player_name: str,
                                  season: str) -> Optional[pl.DataFrame]:
        """Fetch player stats asynchronously"""
        self._rate_limit()
        try:
            from nba_api.stats.endpoints import playergamelog
            player_log = playergamelog.PlayerGameLog(
                player_id=str(player_id),
                season=season
            )
            df = pl.from_pandas(player_log.get_data_frames()[0])
            if not df.is_empty():
                return (df.lazy()
                        .with_columns([
                    pl.lit(player_name).alias("PLAYER_NAME"),
                    pl.lit(season).alias("SEASON")
                ])
                        .collect()
                        )
        except Exception as e:
            print(f"Error fetching stats for player {player_id} in season {season}: {e}")
        return None

    @cache_decorator(expire_in=3600)  # Cache for 1 hour
    def get_player_stats(self, season: str = None) -> Optional[pl.DataFrame]:
        """Fetch and process player stats for specified season(s)"""
        # Get current roster
        self._rate_limit()
        roster = commonteamroster.CommonTeamRoster(team_id=self.team_id)
        roster_df = pl.from_pandas(roster.get_data_frames()[0])

        # Create player ID to name mapping
        player_mapping = dict(zip(roster_df["PLAYER_ID"], roster_df["PLAYER"]))

        seasons_to_fetch = [season] if season else self.seasons
        all_stats = []

        for s in seasons_to_fetch:
            # Fetch player stats in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_player = {
                    executor.submit(
                        self._fetch_player_stats_async,
                        player_id,
                        player_mapping[player_id],
                        s
                    ): player_id
                    for player_id in player_mapping
                }

                for future in concurrent.futures.as_completed(future_to_player):
                    result = future.result()
                    if result is not None:
                        all_stats.append(result)

        if not all_stats:
            return None

        # Process all stats at once
        return (pl.concat(all_stats)
                .lazy()
                .with_columns([
            pl.col("GAME_DATE").str.strptime(pl.Date, "%b %d, %Y", strict=False),
            pl.col("FG_PCT").cast(pl.Float32),
            pl.col("FG3_PCT").cast(pl.Float32),
            pl.col("FT_PCT").cast(pl.Float32),
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
            "SEASON",
            "PTS",
            "REB",
            "AST",
            "FG_PCT",
            "STL",
            "BLK",
            "TOV"
        ])
                .sort(["SEASON", "PLAYER_NAME", "GAME_DATE"],
                      descending=[True, False, True])
                .collect()
                )

    @cache_decorator(expire_in=3600)
    def get_season_comparison(self) -> Optional[pl.DataFrame]:
        """Compare stats across seasons"""
        games_df = self.get_team_games()
        if games_df is None:
            return None

        return (games_df
                .lazy()
                .group_by("SEASON")
                .agg([
            pl.col("PTS").mean().round(1).alias("AVG_PTS"),
            pl.col("FG_PCT").mean().round(3).alias("AVG_FG_PCT"),
            pl.col("FG3_PCT").mean().round(3).alias("AVG_FG3_PCT"),
            pl.col("REB").mean().round(1).alias("AVG_REB"),
            pl.col("AST").mean().round(1).alias("AVG_AST"),
            pl.col("PTS").count().alias("GAMES_PLAYED")
        ])
                .sort("SEASON", descending=True)
                .collect()
                )

    def clear_cache(self):
        """Clear all caches"""
        self.cache.clear()
