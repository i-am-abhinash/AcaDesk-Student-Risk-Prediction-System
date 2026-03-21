from cryptography.fernet import Fernet
import hashlib
import os

# 1. LOAD OR CREATE A SECRET KEY (Keeps encryption consistent)
KEY_FILE = "secret.key"
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "wb") as f:
        f.write(Fernet.generate_key())

with open(KEY_FILE, "rb") as f:
    key = f.read()

cipher = Fernet(key)

def hash_password(plain_password):
    """ One-way hash for User Login """
    return hashlib.sha256(plain_password.encode()).hexdigest()

def encrypt_text(text):
    """ Reversible encryption for ERP Database Passwords """
    if not text: return ""
    return cipher.encrypt(text.encode()).decode()

def decrypt_text(encrypted_text):
    """ Decrypts the ERP password so the app can connect """
    if not encrypted_text: return ""
    try:
        return cipher.decrypt(encrypted_text.encode()).decode()
    except:
        return ""