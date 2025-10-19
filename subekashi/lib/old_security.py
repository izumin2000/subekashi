# 旧security
from config.settings import SECRET_KEY
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import binascii
import hashlib


SYMBOLS = ".◘#∴¹▼᠂（◆ን∮♭▘・ｷᛜ"

def sha256(check) :
    check += SECRET_KEY
    return hashlib.sha256(check.encode()).hexdigest()

# ハッシュを利用して鍵を指定の長さに調整する
def derive_key(key, length):
    return hashlib.sha256(key.encode()).digest()[:length]

# 16進数を記号に
def hex_to_symbols(hex_str):
    return "".join(SYMBOLS[int(c, 16)] for c in hex_str.lower())

# 記号を16進数に
def symbols_to_hex(symbol_str):
    symbol_map = {symbol: hex(i)[2:] for i, symbol in enumerate(SYMBOLS)}
    return "".join(symbol_map[c] for c in symbol_str)

# IPアドレスから記号暗号に
def encrypt(ip):
    key_bytes = derive_key(SECRET_KEY, 16)
    cipher = AES.new(key_bytes, AES.MODE_CBC)
    formated_ip = ip
    ciphertext = cipher.encrypt(pad(formated_ip.encode(), AES.block_size))
    encrypted_hex = binascii.hexlify(cipher.iv + ciphertext).decode()
    return hex_to_symbols(encrypted_hex)

# 記号暗号からIPアドレスに
def decrypt(ciphertext):
    key_bytes = derive_key(SECRET_KEY, 16)
    hex_str = symbols_to_hex(ciphertext)
    raw_data = binascii.unhexlify(hex_str)
    iv, ciphertext = raw_data[:AES.block_size], raw_data[AES.block_size:]
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    formatted_ip = unpad(cipher.decrypt(ciphertext), AES.block_size).decode()
    return formatted_ip