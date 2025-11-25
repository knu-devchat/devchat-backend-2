from functools import lru_cache
from django.conf import settings

@lru_cache(maxsize=1)
def get_master_key() -> bytes:
    key = getattr(settings, "MASTER_KEY", None)
    if key is None:
        raise RuntimeError("MASTER_KEY not configured in settings")
    return key