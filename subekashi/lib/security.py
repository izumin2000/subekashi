from config.settings import SECRET_KEY
import hashlib


def sha256(check) :
    check += SECRET_KEY
    return hashlib.sha256(check.encode()).hexdigest()
