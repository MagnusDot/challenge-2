import hashlib
import json
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

class RequestCachePlugin:

    def __init__(
        self,
        ttl_seconds: int = 3600,
        max_size: int = 1000,
    ):

        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size

    def _generate_cache_key(self, prompt: str, model: str) -> str:

        content = f"{model}:{prompt}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _is_expired(self, cached_entry: Dict[str, Any]) -> bool:

        cached_time = datetime.fromisoformat(cached_entry['timestamp'])
        age = (datetime.now() - cached_time).total_seconds()
        return age > self.ttl_seconds

    def _cleanup_expired(self) -> None:

        expired_keys = [
            key for key, entry in self.cache.items()
            if self._is_expired(entry)
        ]
        for key in expired_keys:
            del self.cache[key]

    def _enforce_max_size(self) -> None:

        if len(self.cache) <= self.max_size:
            return

        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1]['timestamp']
        )
        entries_to_remove = len(self.cache) - self.max_size
        for key, _ in sorted_entries[:entries_to_remove]:
            del self.cache[key]

    async def before_model_callback(
        self,
        model: str,
        prompt: str,
        **kwargs: Any
    ) -> Optional[Dict[str, Any]]:

        if len(self.cache) > 0 and len(self.cache) % 100 == 0:
            self._cleanup_expired()

        cache_key = self._generate_cache_key(prompt, model)

        if cache_key in self.cache:
            entry = self.cache[cache_key]

            if not self._is_expired(entry):

                return {
                    'cached': True,
                    'response': entry['response'],
                    'metadata': entry.get('metadata', {})
                }
            else:

                del self.cache[cache_key]

        return None

    async def after_model_callback(
        self,
        model: str,
        prompt: str,
        response: Any,
        **kwargs: Any
    ) -> None:

        cache_key = self._generate_cache_key(prompt, model)

        self._cleanup_expired()
        self._enforce_max_size()

        self.cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'model': model,
            'metadata': kwargs.get('metadata', {})
        }

    def clear_cache(self) -> None:

        self.cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:

        total_entries = len(self.cache)
        expired_count = sum(
            1 for entry in self.cache.values()
            if self._is_expired(entry)
        )

        return {
            'total_entries': total_entries,
            'active_entries': total_entries - expired_count,
            'expired_entries': expired_count,
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds
        }