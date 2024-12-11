import yaml
from pathlib import Path
from typing import Dict, Any
from functools import lru_cache

class Config:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    @lru_cache()
    def _load_config(self):
        """Load config file with caching"""
        # Look for config file in src/config
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        if not config_path.exists():
            # Use default values if config file doesn't exist
            self._config = {
                'api': {
                    'nba': {
                        'delay': 1.5,
                        'team_id': "1610612761"  # Raptors ID
                    }
                },
                'dashboard': {
                    'refresh_rate': 30,
                    'default_season': "2023-24",
                    'charts': {
                        'colors': {
                            'primary': "#CE1141",
                            'secondary': "#000000",
                            'accent': "#A1A1A4"
                        }
                    }
                },
                'ml': {
                    'model': {
                        'update_frequency': 86400,
                        'features': [
                            'pts_ma_5',
                            'fg_pct_ma_5',
                            'fg3_pct_ma_5',
                            'reb_ma_5',
                            'ast_ma_5'
                        ],
                        'window_sizes': {
                            'short': 5,
                            'medium': 10,
                            'long': 20
                        },
                        'training': {
                            'test_size': 0.2,
                            'random_state': 42
                        }
                    }
                },
                'paths': {
                    'models': 'models',
                    'data': 'data'
                }
            }
            return

        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get a config value using dot notation"""
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value

    @property
    def nba_delay(self) -> float:
        return self.get('api', 'nba', 'delay', default=1.5)

    @property
    def team_id(self) -> str:
        return str(self.get('api', 'nba', 'team_id', default="1610612761"))

    @property
    def refresh_rate(self) -> int:
        return self.get('dashboard', 'refresh_rate', default=30)

    @property
    def default_season(self) -> str:
        return self.get('dashboard', 'default_season', default="2023-24")

    @property
    def chart_colors(self) -> dict:
        return self.get('dashboard', 'charts', 'colors', default={
            'primary': "#CE1141",
            'secondary': "#000000",
            'accent': "#A1A1A4"
        })

    @property
    def model_features(self) -> list:
        return self.get('ml', 'model', 'features', default=[
            'pts_ma_5',
            'fg_pct_ma_5',
            'fg3_pct_ma_5',
            'reb_ma_5',
            'ast_ma_5'
        ])

    @property
    def window_sizes(self) -> dict:
        return self.get('ml', 'model', 'window_sizes', default={
            'short': 5,
            'medium': 10,
            'long': 20
        })

    @property
    def model_update_frequency(self) -> int:
        return self.get('ml', 'model', 'update_frequency', default=86400)

    @property
    def model_path(self) -> str:
        """Get the path to save/load models"""
        return self.get('paths', 'models', default='models')

    @property
    def data_path(self) -> str:
        """Get the path for data storage"""
        return self.get('paths', 'data', default='data')
