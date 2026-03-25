"""
Cache service for Adobe Analytics API responses
Implements file-based caching using JSON files with per-key TTL support
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


class CacheService:
    """File-based cache for API responses with per-key expiration"""

    def __init__(self, cache_dir: str = None):
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

    def _load_metadata(self, cache_name: str) -> dict:
        """Load metadata dict from file, returning empty dict on failure"""
        meta_path = self._get_metadata_path(cache_name)
        if not meta_path.exists():
            return {}
        try:
            with open(meta_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_metadata(self, cache_name: str, metadata: dict) -> None:
        """Persist metadata dict to file"""
        meta_path = self._get_metadata_path(cache_name)
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def get(self, cache_name: str, key: str) -> Any | None:
        """
        Get a value from the cache.

        Returns cached value or None if not found/expired.
        """
        cache_path = self._get_cache_path(cache_name)

        if not cache_path.exists():
            return None

        if self._is_key_expired(cache_name, key):
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                return cache_data.get(key)
        except (json.JSONDecodeError, IOError):
            return None

    def set(self, cache_name: str, key: str, value: Any, ttl_hours: float = DEFAULT_TTL_HOURS) -> None:
        """
        Set a value in the cache with a per-key TTL.
        """
        cache_path = self._get_cache_path(cache_name)

        # Load existing cache data (only non-expired entries)
        cache_data = {}
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                cache_data = {}

        # Update cache data
        cache_data[key] = value
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2, default=str)

        # Update per-key metadata
        metadata = self._load_metadata(cache_name)
        metadata['cache_name'] = cache_name
        if 'keys' not in metadata:
            metadata['keys'] = {}
        metadata['keys'][key] = {
            'created': datetime.now().isoformat(),
            'ttl_hours': ttl_hours,
        }
        # Keep a top-level 'created' for backwards compatibility (most recent write)
        metadata['created'] = datetime.now().isoformat()
        self._save_metadata(cache_name, metadata)

    def _is_key_expired(self, cache_name: str, key: str) -> bool:
        """Check if a specific cache key is expired based on its per-key TTL"""
        metadata = self._load_metadata(cache_name)
        key_meta = metadata.get('keys', {}).get(key)

        if not key_meta:
            # Legacy metadata format — fall back to global 'created' with 1h TTL
            created_str = metadata.get('created')
            if not created_str:
                return True
            try:
                created = datetime.fromisoformat(created_str)
                return (datetime.now() - created).total_seconds() > 3600
            except (ValueError, TypeError):
                return True

        try:
            created = datetime.fromisoformat(key_meta['created'])
            ttl_seconds = key_meta.get('ttl_hours', DEFAULT_TTL_HOURS) * 3600
            return (datetime.now() - created).total_seconds() > ttl_seconds
        except (ValueError, TypeError, KeyError):
            return True

    def _is_expired(self, cache_name: str) -> bool:
        """Check if the whole cache is expired (legacy compat — checks global timestamp)"""
        metadata = self._load_metadata(cache_name)
        created_str = metadata.get('created')
        if not created_str:
            return True
        try:
            created = datetime.fromisoformat(created_str)
            return (datetime.now() - created).total_seconds() > 3600
        except (ValueError, TypeError):
            return True

    def get_info(self, cache_name: str) -> dict:
        """Get cache information"""
        meta_path = self._get_metadata_path(cache_name)
        cache_path = self._get_cache_path(cache_name)

        info = {
            'cache_name': cache_name,
            'exists': cache_path.exists(),
            'created': None,
            'age_mins': None,
            'expired': True,
            'size_bytes': 0,
            'keys': {},
        }

        metadata = self._load_metadata(cache_name)
        if not metadata:
            return info

        # Top-level info (most recent write)
        created_str = metadata.get('created')
        if created_str:
            try:
                created = datetime.fromisoformat(created_str)
                age_seconds = (datetime.now() - created).total_seconds()
                info['created'] = created_str
                info['age_mins'] = round(age_seconds / 60, 1)
                info['expired'] = age_seconds > 3600
            except (ValueError, TypeError):
                pass

        if cache_path.exists():
            info['size_bytes'] = cache_path.stat().st_size

        # Per-key info
        for key, key_meta in metadata.get('keys', {}).items():
            try:
                key_created = datetime.fromisoformat(key_meta['created'])
                ttl_hours = key_meta.get('ttl_hours', DEFAULT_TTL_HOURS)
                age_seconds = (datetime.now() - key_created).total_seconds()
                info['keys'][key] = {
                    'created': key_meta['created'],
                    'age_mins': round(age_seconds / 60, 1),
                    'ttl_hours': ttl_hours,
                    'expired': age_seconds > (ttl_hours * 3600),
                }
            except (ValueError, TypeError, KeyError):
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

    def clear_key(self, cache_name: str, key: str) -> None:
        """Clear a single key from the cache"""
        cache_path = self._get_cache_path(cache_name)

        # Remove the key from cache data
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)
                cache_data.pop(key, None)
                with open(cache_path, 'w') as f:
                    json.dump(cache_data, f, indent=2, default=str)
            except (json.JSONDecodeError, IOError):
                pass

        # Remove the key from metadata
        metadata = self._load_metadata(cache_name)
        keys_meta = metadata.get('keys', {})
        if key in keys_meta:
            del keys_meta[key]
            self._save_metadata(cache_name, metadata)

    def clear_all(self) -> None:
        """Clear all caches"""
        for file in self.cache_dir.glob('*.json'):
            file.unlink()

    def get_or_set(self, cache_name: str, key: str, fetch_func: Callable,
                   ttl_hours: float = DEFAULT_TTL_HOURS) -> Any:
        """
        Get from cache or fetch and cache.

        Args:
            cache_name: Name of the cache (e.g., report suite ID)
            key: Key within the cache
            fetch_func: Function to call if cache miss
            ttl_hours: How long to keep this key (default: 1 hour)
        """
        cached = self.get(cache_name, key)
        if cached is not None:
            return cached

        value = fetch_func()
        self.set(cache_name, key, value, ttl_hours=ttl_hours)
        return value
