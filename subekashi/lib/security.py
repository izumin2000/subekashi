# 新security
from config.settings import SECRET_KEY
import hashlib
import ipaddress
from Crypto.Cipher import AES


SYMBOLS = ".◘#∴¹▼᠂（◆ን"


def ip_to_int(ip):
    return int(ipaddress.ip_address(ip))


def int_to_ip(num):
    return str(ipaddress.ip_address(num))


def pad(data, block_size = 16):
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len]) * pad_len


def unpad(data):
    pad_len = data[-1]
    return data[:-pad_len]


def encode_base_n(num):
    base = len(SYMBOLS)
    if num == 0:
        return SYMBOLS[0]
    result = ""
    while num > 0:
        num, rem = divmod(num, base)
        result = SYMBOLS[rem] + result
    return result


def decode_base_n(encoded):
    base = len(SYMBOLS)
    num = 0
    for char in encoded:
        num = num * base + SYMBOLS.index(char)
    return num


def sha256(check):
    check += SECRET_KEY
    return hashlib.sha256(check.encode()).digest()


def encrypt(ip):
    # IP → 整数 → バイト列
    ip_num = ip_to_int(ip)
    ip_bytes = ip_num.to_bytes((ip_num.bit_length() + 7) // 8 or 1, "big")

    # AES暗号化
    cipher = AES.new(sha256(""), AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(ip_bytes))

    # 数値に変換 → カスタム文字セットでエンコード
    num = int.from_bytes(encrypted, "big")
    return encode_base_n(num)


def decrypt(encrypted):
    # カスタム文字列 → 数値 → バイト列
    num = decode_base_n(encrypted)
    enc_bytes = num.to_bytes((num.bit_length() + 7) // 8 or 1, "big")

    # AES復号
    cipher = AES.new(sha256(""), AES.MODE_ECB)
    decrypted = unpad(cipher.decrypt(enc_bytes))

    # 整数 → IP
    ip_num = int.from_bytes(decrypted, "big")
    return int_to_ip(ip_num)