import yaml
import os

class ConfigLoader:
    """
    Loads YAML configuration for the trading system.
    Provides safe defaults and easy access to settings.
    """

    def __init__(self, config_path="config/settings.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        """Read YAML config and return dict with defaults."""
        if not os.path.exists(self.config_path):
            print(f"[ConfigLoader] ⚠️ Config not found at {self.config_path}, using defaults.")
            return {
                "time_range": {"start": "09:30", "end": "10:00"},
                "risk": {"stop_loss": -450, "profit_target": 500, "breakeven_profit": 150},
                "strategy": {"ema_period": 9, "position_size": 1},
            }

        with open(self.config_path, "r") as file:
            try:
                data = yaml.safe_load(file)
                return data
            except yaml.YAMLError as e:
                print(f"[ConfigLoader] ⚠️ YAML error: {e}")
                return {}

    def get(self, section, key=None, default=None):
        """Access config sections or single values."""
        if key:
            return self.config.get(section, {}).get(key, default)
        return self.config.get(section, default)
