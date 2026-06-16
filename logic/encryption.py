from cryptography.fernet import Fernet
import bcrypt
import os
import pathlib

# 1. LOAD OR CREATE A SECRET KEY (Keeps encryption consistent)
# Default to ~/.acadesk/secret.key, configurable via ACADESK_KEY_PATH
default_key_path = pathlib.Path.home() / ".acadesk" / "secret.key"
KEY_FILE = os.environ.get("ACADESK_KEY_PATH", str(default_key_path))

# Ensure directory exists if using the default or a file within a directory
key_path_obj = pathlib.Path(KEY_FILE)
if not key_path_obj.exists():
    key_path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(KEY_FILE, "wb") as f:
        f.write(Fernet.generate_key())
    print(f"WARNING: A new encryption key was generated at {KEY_FILE}. Back up this file — losing it will make all saved ERP passwords unrecoverable.")

with open(KEY_FILE, "rb") as f:
    key = f.read()

cipher = Fernet(key)

def hash_password(plain_password):
    """ One-way hash for User Login using bcrypt """
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_password(plain_password, hashed_password):
    """ Verifies a plain text password against a bcrypt hash, with legacy sha256 fallback """
    try:
        if hashed_password.startswith("$2") and len(hashed_password) == 60:
            return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
        else:
            import hashlib
            legacy_hash = hashlib.sha256(plain_password.encode()).hexdigest()
            return legacy_hash == hashed_password
    except Exception as e:
        print(f"Exception caught: {e}")
        return False

def encrypt_text(text):
    """ Reversible encryption for ERP Database Passwords """
    if not text: return ""
    return cipher.encrypt(text.encode()).decode()

def decrypt_text(encrypted_text):
    """ Decrypts the ERP password so the app can connect """
    if not encrypted_text: return ""
    try:
        return cipher.decrypt(encrypted_text.encode()).decode()
    except Exception as e:
        print(f"Exception caught: {e}")
        return ""