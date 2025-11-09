"""
Configuration Manager - Handles system configuration with CLI support
Provides configurable retry counts, backoff settings, and timeouts
"""

import json
import os

class Config:
    """Manages system configuration with persistence"""

    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.defaults = {
            'storage_file': 'jobs.json',
            'max_retries': 3,
            'backoff_base': 1,
            'backoff_max': 60,
            'job_timeout': 300
        }
        self._load_config()

    def _load_config(self):
        """Load configuration from file or initialize with defaults"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new config keys
                    self.config = {**self.defaults, **loaded}
            except json.JSONDecodeError:
                print(f"Warning: Invalid config file, using defaults")
                self.config = self.defaults.copy()
        else:
            self.config = self.defaults.copy()
            self._save_config()

    def _save_config(self):
        """Persist configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get(self, key: str, default=None):
        """Get configuration value with fallback"""
        return self.config.get(key, default)

    def set(self, key: str, value):
        """Set configuration value with type validation"""
        # Type conversion based on key
        if key in ['max_retries', 'job_timeout']:
            try:
                value = int(value)
            except ValueError:
                raise ValueError(f"{key} must be an integer")

        elif key in ['backoff_base', 'backoff_max']:
            try:
                value = float(value)
            except ValueError:
                raise ValueError(f"{key} must be a number")

        self.config[key] = value
        self._save_config()

    def show(self):
        """Display all configuration settings"""
        print("\n=== Configuration ===")
        for key, value in sorted(self.config.items()):
            print(f"  {key:20} = {value}")
        print()

    def reset(self):
        """Reset configuration to defaults"""
        self.config = self.defaults.copy()
        self._save_config()
