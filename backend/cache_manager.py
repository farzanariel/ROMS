import asyncio
import time
import logging
from typing import Dict, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DataCache:
    def __init__(self, cache_duration_minutes: int = 10):  # Increased from 5 to 10 minutes
        self.cache: Dict[str, Tuple[pd.DataFrame, float]] = {}
        self.cache_duration = cache_duration_minutes * 60  # Convert to seconds
        self.last_access: Dict[str, float] = {}
        # Add performance metrics
        self.cache_hits = 0
        self.cache_misses = 0
        
    def get_cache_key(self, sheet_url: str, worksheet_name: str = None) -> str:
        """Generate cache key for sheet/worksheet combination"""
        return f"{sheet_url}::{worksheet_name or 'ALL_WORKSHEETS'}"
    
    def is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid"""
        if key not in self.cache:
            return False
        
        _, timestamp = self.cache[key]
        return (time.time() - timestamp) < self.cache_duration
    
    def get_cached_data(self, sheet_url: str, worksheet_name: str = None) -> Optional[pd.DataFrame]:
        """Get cached data if valid"""
        key = self.get_cache_key(sheet_url, worksheet_name)
        
        if self.is_cache_valid(key):
            data, _ = self.cache[key]
            self.last_access[key] = time.time()
            self.cache_hits += 1
            logger.info(f"⚡ Cache HIT for {key} (Hit rate: {self.get_hit_rate():.1%})")
            return data.copy()  # Return copy to prevent mutations
        
        self.cache_misses += 1
        logger.info(f"💾 Cache MISS for {key} (Hit rate: {self.get_hit_rate():.1%})")
        return None
    
    def set_cached_data(self, sheet_url: str, data: pd.DataFrame, worksheet_name: str = None):
        """Cache the data with timestamp"""
        key = self.get_cache_key(sheet_url, worksheet_name)
        self.cache[key] = (data.copy(), time.time())
        self.last_access[key] = time.time()
        logger.info(f"Cached data for {key}: {len(data)} rows")
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
    
    def clear_cache(self, sheet_url: str = None):
        """Clear cache for specific sheet or all cache"""
        if sheet_url:
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(sheet_url)]
            for key in keys_to_remove:
                del self.cache[key]
                if key in self.last_access:
                    del self.last_access[key]
            logger.info(f"Cleared cache for {sheet_url}")
        else:
            self.cache.clear()
            self.last_access.clear()
            logger.info("Cleared all cache")
    
    def cleanup_old_entries(self):
        """Remove old cache entries to prevent memory buildup"""
        current_time = time.time()
        expired_keys = []
        
        for key, (_, timestamp) in self.cache.items():
            if (current_time - timestamp) > (self.cache_duration * 2):  # Remove after 2x cache duration
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
            if key in self.last_access:
                del self.last_access[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

class RateLimiter:
    def __init__(self, max_requests_per_minute: int = 300):  # Increased from 100 to 300 since quota usage is low
        self.max_requests = max_requests_per_minute
        self.requests: list = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait if necessary to respect rate limits"""
        async with self.lock:
            current_time = time.time()
            
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests if current_time - req_time < 60]
            
            # Check if we're at the limit
            if len(self.requests) >= self.max_requests:
                # Calculate wait time until oldest request expires
                wait_time = 60 - (current_time - self.requests[0]) + 0.05  # Reduced buffer from 0.1 to 0.05
                logger.warning(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)
                
                # Clean up again after waiting
                current_time = time.time()
                self.requests = [req_time for req_time in self.requests if current_time - req_time < 60]
            
            # Record this request
            self.requests.append(current_time)
            logger.debug(f"Rate limiter: {len(self.requests)}/{self.max_requests} requests in last minute")

# Global instances
data_cache = DataCache(cache_duration_minutes=5)  # 5-minute cache
rate_limiter = RateLimiter(max_requests_per_minute=300)  # Optimized for low quota usage

async def periodic_cache_cleanup():
    """Background task to clean up expired cache entries"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            data_cache.cleanup_old_entries()
        except Exception as e:
            logger.error(f"Error in cache cleanup: {e}")
