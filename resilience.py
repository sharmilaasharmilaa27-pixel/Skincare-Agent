import time
import functools
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable, Any
from enum import Enum

STATE_FILE = Path(os.path.join(tempfile.gettempdir(), "circuit_state.json"))

class CircuitOpenError(Exception):
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30, expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CIRCUIT_BREAKER_STATES.CLOSED
        self._load_state()

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE) as f:
                    data = json.load(f)
                    self.state = CIRCUIT_BREAKER_STATES(data["state"])
                    self.failures = data["failures"]
                    self.last_failure_time = datetime.fromisoformat(data["last_failure_time"]) if data.get("last_failure_time") else None
            except Exception:
                pass

    def _save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump({"state": self.state.name, "failures": self.failures,
                        "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None}, f)

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CIRCUIT_BREAKER_STATES.OPEN:
            if self.last_failure_time and datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = CIRCUIT_BREAKER_STATES.HALF_OPEN
                self._save_state()
            else:
                raise CircuitOpenError(f"Circuit OPEN. Last failure: {self.last_failure_time}")
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failures = 0
        self.state = CIRCUIT_BREAKER_STATES.CLOSED
        self._save_state()

    def _on_failure(self):
        self.failures += 1
        self.last_failure_time = datetime.now()
        if self.failures >= self.failure_threshold:
            self.state = CIRCUIT_BREAKER_STATES.OPEN
        self._save_state()

    def is_open(self) -> bool:
        return self.state == CIRCUIT_BREAKER_STATES.OPEN

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0, exceptions: tuple = (Exception,)):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay)
                    delay = min(delay * 2, max_delay)
            raise RuntimeError("Max retries exceeded")
        return wrapper
    return decorator

def fallback(default_response: str):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                return default_response
        return wrapper
    return decorator

class GracefulDegradation:
    def __init__(self):
        self.semantic_search_cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        self.llm_cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        self.ingredient_cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

    def search_docs_with_fallback(self, query: str, primary_search, fallback_search) -> str:
        try:
            return self.semantic_search_cb.call(primary_search, query)
        except (CircuitOpenError, Exception):
            return fallback_search(query)

    def llm_with_fallback(self, prompt: str, primary_llm, fallback_llm) -> str:
        try:
            return self.llm_cb.call(primary_llm, prompt)
        except (CircuitOpenError, Exception):
            return fallback_llm(prompt)

    def ingredient_with_fallback(self, name: str, primary_lookup, fallback_lookup) -> str:
        try:
            return self.ingredient_cb.call(primary_lookup, name)
        except (CircuitOpenError, Exception):
            return fallback_lookup(name)

import tempfile

def _get_cache_dir() -> str:
    return os.path.join(tempfile.gettempdir(), "glowai_cache")

def get_cached_response(cache_key: str) -> Optional[str]:
    cache_path = Path(_get_cache_dir()) / f"{cache_key}.json"
    if cache_path.exists():
        try:
            with open(cache_path) as f:
                data = json.load(f)
                if datetime.fromisoformat(data["expires_at"]) > datetime.now():
                    return data["response"]
        except Exception:
            pass
    return None

def set_cached_response(cache_key: str, response: str, ttl_seconds: int = 3600):
    cache_dir = _get_cache_dir()
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = Path(cache_dir) / f"{cache_key}.json"
    try:
        with open(cache_path, "w") as f:
            json.dump({"response": response, "expires_at": (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()}, f)
    except Exception:
        pass
