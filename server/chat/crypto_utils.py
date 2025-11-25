import base64
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
import pyotp
from secrets import token_bytes


# 마스터키 가져오기 (.env의 MASTER_KEY_B64 또는 settings.MASTER_KEY 사용)
@lru_cache(maxsize=1)
def get_master_key() -> bytes:
    key = getattr(settings, "MASTER_KEY", None)

    if key is None:
        b64_key = os.environ.get("MASTER_KEY_B64")
        if b64_key:
            try:
                key = base64.b64decode(b64_key)
            except Exception as exc:
                raise RuntimeError("MASTER_KEY_B64 is not valid base64") from exc

    # AES 키 길이: 16, 24, 32 바이트만 허용
    if key is None or len(key) not in (16, 24, 32):
        raise RuntimeError("MASTER_KEY not configured in settings or .env")

    return key

# 채팅방 고유 TOTP 비밀키 생성
def generate_pseudo_number():
    """
    채팅방 고유 TOTP 비밀키 생성:
      - pyotp.random_base32()로 base32 문자열 생성
      - AES-GCM 암호화를 위해 ASCII bytes로 변환
    """
    # TOTP용 base32 비밀키 문자열 (예: 'JBSWY3DPEHPK3PXP...')
    secret_str = pyotp.random_base32()
    secret_key = secret_str.encode("ascii")  # 암호화에 사용할 bytes

    # AES-GCM 권장 IV 길이: 12 bytes
    iv = token_bytes(12)

    return secret_key, iv

# AES-GCM 암호화/복호화 함수
def encrypt_aes_gcm(secret_key: bytes, iv: bytes) -> str:
    """
    AES-GCM으로 secret_key 를 암호화하고,
    (iv + ciphertext) 바이트를 base64 문자열로 인코딩해서 반환.
    """
    master_key = get_master_key()
    aesgcm = AESGCM(master_key)

    # ciphertext에는 tag까지 포함됨
    ciphertext = aesgcm.encrypt(iv, secret_key, None)

    # iv + ciphertext 를 하나로 합쳐 base64 인코딩
    return base64.b64encode(iv + ciphertext).decode("ascii")


def decrypt_aes_gcm(b64_data: str) -> bytes:
    """
    base64(iv + ciphertext) 문자열을 복호화해
    원래 secret_key(bytes)를 반환.
    """
    master_key = get_master_key()
    data = base64.b64decode(b64_data)

    iv = data[:12]
    ciphertext = data[12:]

    aesgcm = AESGCM(master_key)
    return aesgcm.decrypt(iv, ciphertext, None)