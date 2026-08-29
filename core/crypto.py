import base64
from Crypto.Cipher import AES
from google.protobuf import message

MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')

def pad(text: bytes) -> bytes:
    padding_length = AES.block_size - (len(text) % AES.block_size)
    return text + bytes([padding_length] * padding_length)

def aes_cbc_encrypt(plaintext: bytes) -> bytes:
    aes = AES.new(MAIN_KEY, AES.MODE_CBC, MAIN_IV)
    return aes.encrypt(pad(plaintext))

def encode_varint(value: int) -> bytes:
    bits = value & 0x7f
    value >>= 7
    res = bytearray()
    while value:
        res.append(0x80 | bits)
        bits = value & 0x7f
        value >>= 7
    res.append(bits)
    return bytes(res)

def decode_protobuf(encoded_data: bytes, message_type: message.Message) -> message.Message:
    instance = message_type()
    instance.ParseFromString(encoded_data)
    return instance