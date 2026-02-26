import secrets
import hmac
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings

cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_token(token: str) -> str:
    return cipher_suite.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    return cipher_suite.decrypt(encrypted_token.encode()).decode()

def generate_secret_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)

def verify_secret_token(received_token: str, expected_token: str) -> bool:
    if not received_token or not expected_token:
        return False
    return hmac.compare_digest(received_token, expected_token)

def get_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def verify_hash(plain_data: str, hashed_data: str) -> bool:
    return get_hash(plain_data) == hashed_data
