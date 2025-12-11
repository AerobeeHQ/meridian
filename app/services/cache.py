"""
Cache service for Adobe Analytics API responses
Implements hourly file-based caching using JSON files
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


class CacheService:
    """File-based cache for API responses with hourly expiration"""

    def __init__(self, cache_dir: str = None):
        """
        Initialize the cache service

        Args:
            cache_dir: Directory to store cache files (default: ./cache)
        """
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'cache'
            )

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_path(self, cache_name: str) -> Path:
        """Get the path for a cache file"""
        return self.cache_dir / f"{cache_name}.json"

    def _get_metadata_path(self, cache_name: str) -> Path:
        """Get the path for cache metadata file"""
        return self.cache_dir / f"{cache_name}_meta.json"

    def get(self, cache_name: str, key: str) -> Any | None:
        """
        Get a value from the cache

        Args:
            cache_name: Name of the cache (e.g., report suite ID)
            key: Key within the cache

        Returns:
            Cached value or None if not found/expired
        """
        cache_path = self._get_cache_path(cache_name)

        if not cache_path.exists():
            return None

        # Check if cache is expired (older than 1 hour)
        if self._is_expired(cache_name):
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                return cache_data.get(key)
        except (json.JSONDecodeError, IOError):
            return None

    def set(self, cache_name: str, key: str, value: Any) -> None:
        """
        Set a value in the cache

        Args:
            cache_name: Name of the cache
            key: Key within the cache
            value: Value to store
        """
        cache_path = self._get_cache_path(cache_name)
        meta_path = self._get_metadata_path(cache_name)

        # Load existing cache or create new
        cache_data = {}
        if cache_path.exists() and not self._is_expired(cache_name):
            try:
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                cache_data = {}

        # Update cache
        cache_data[key] = value

        # Write cache data
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2, default=str)

        # Update metadata
        metadata = {
            'created': datetime.now().isoformat(),
            'cache_name': cache_name
        }
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _is_expired(self, cache_name: str) -> bool:
        """Check if cache is expired (older than 1 hour)"""
        meta_path = self._get_metadata_path(cache_name)

        if not meta_path.exists():
            return True

        try:
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            created = datetime.fromisoformat(metadata['created'])
            age_seconds = (datetime.now() - created).total_seconds()

            # Expire after 1 hour (3600 seconds)
            return age_seconds > 3600
        except (json.JSONDecodeError, IOError, KeyError, ValueError):
            return True

    def get_info(self, cache_name: str) -> dict:
        """
        Get cache information

        Args:
            cache_name: Name of the cache

        Returns:
            Dictionary with cache metadata
        """
        meta_path = self._get_metadata_path(cache_name)
        cache_path = self._get_cache_path(cache_name)

        info = {
            'cache_name': cache_name,
            'exists': cache_path.exists(),
            'created': None,
            'age_mins': None,
            'expired': True,
            'size_bytes': 0
        }

        if not meta_path.exists():
            return info

        try:
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            created = datetime.fromisoformat(metadata['created'])
            age_seconds = (datetime.now() - created).total_seconds()

            info['created'] = metadata['created']
            info['age_mins'] = round(age_seconds / 60, 1)
            info['expired'] = age_seconds > 3600

            if cache_path.exists():
                info['size_bytes'] = cache_path.stat().st_size

        except (json.JSONDecodeError, IOError, KeyError, ValueError):
            pass

        return info

    def clear(self, cache_name: str) -> None:
        """Clear a specific cache"""
        cache_path = self._get_cache_path(cache_name)
        meta_path = self._get_metadata_path(cache_name)

        if cache_path.exists():
            cache_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

    def clear_all(self) -> None:
        """Clear all caches"""
        for file in self.cache_dir.glob('*.json'):
            file.unlink()

    def get_or_set(self, cache_name: str, key: str, fetch_func: Callable) -> Any:
        """
        Get from cache or fetch and cache

        Args:
            cache_name: Name of the cache
            key: Key within the cache
            fetch_func: Function to call if cache miss

        Returns:
            Cached or fetched value
        """
        cached = self.get(cache_name, key)
        if cached is not None:
            return cached

        value = fetch_func()
        self.set(cache_name, key, value)
        return value

