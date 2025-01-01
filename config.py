import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Default configuration path
CONFIG_DIR = os.path.join(str(Path.home()), '.png_to_webp')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

# Preset profiles for different use cases
PRESET_PROFILES = {
    'high_quality': {
        'quality': 95,
        'lossless': True,
        'preserve_timestamps': True,
        'preserve_originals': True,
    },
    'balanced': {
        'quality': 80,
        'lossless': False,
        'preserve_timestamps': True,
        'preserve_originals': True,
    },
    'web_optimized': {
        'quality': 75,
        'lossless': False,
        'preserve_timestamps': False,
        'preserve_originals': True,
    },
    'space_saver': {
        'quality': 60,
        'lossless': False,
        'preserve_timestamps': False,
        'preserve_originals': False,
    }
}

DEFAULT_CONFIG = {
    'default_profile': 'balanced',
    'last_used_settings': None,
    'custom_profiles': {},
    'min_free_space_mb': 500,
    'max_workers': None,  # Will be set based on CPU count
}

class Config:
    def __init__(self):
        self.config_dir = Path(CONFIG_DIR)
        self.config_file = Path(CONFIG_FILE)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file or create default if not exists"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Update with any new default keys
                return {**DEFAULT_CONFIG, **config}
            return DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"Error loading config: {e}")
            return DEFAULT_CONFIG.copy()

    def save_config(self) -> None:
        """Save current configuration to file"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_profile(self, profile_name: Optional[str] = None) -> dict:
        """Get settings for specified profile or default profile if none specified"""
        if not profile_name:
            profile_name = self.config['default_profile']

        # Check custom profiles first
        if profile_name in self.config['custom_profiles']:
            return self.config['custom_profiles'][profile_name]
        # Then check preset profiles
        elif profile_name in PRESET_PROFILES:
            return PRESET_PROFILES[profile_name]
        # Fall back to balanced profile
        return PRESET_PROFILES['balanced']

    def save_custom_profile(self, name: str, settings: dict) -> None:
        """Save a new custom profile"""
        self.config['custom_profiles'][name] = settings
        self.save_config()

    def delete_custom_profile(self, name: str) -> bool:
        """Delete a custom profile"""
        if name in self.config['custom_profiles']:
            del self.config['custom_profiles'][name]
            self.save_config()
            return True
        return False

    def save_last_used_settings(self, settings: dict) -> None:
        """Save the last used settings"""
        self.config['last_used_settings'] = settings
        self.save_config()

    def get_last_used_settings(self) -> Optional[dict]:
        """Get the last used settings"""
        return self.config.get('last_used_settings')

    def set_default_profile(self, profile_name: str) -> bool:
        """Set the default profile"""
        if profile_name in PRESET_PROFILES or profile_name in self.config['custom_profiles']:
            self.config['default_profile'] = profile_name
            self.save_config()
            return True
        return False

    def list_all_profiles(self) -> Dict[str, dict]:
        """List all available profiles (preset and custom)"""
        return {
            **PRESET_PROFILES,
            **self.config['custom_profiles']
        }

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting from the config"""
        return self.config.get(key, default)
