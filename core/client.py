import httpx
import json
import logging
from google.protobuf import json_format, message
from core.crypto import aes_cbc_encrypt, decode_protobuf
from core.auth import get_token_info, SUPPORTED_REGIONS

RELEASEVERSION = "OB54"
USERAGENT = "ART/2.2.0 (Linux; U; Android 14; SAMSUNG_S25 Build/UP1A.240905.001)"

async def dispatch_freefire_request(region: str, endpoint: str, raw_payload: bytes, response_class: message.Message) -> dict:
    region = region.upper()
    if region not in SUPPORTED_REGIONS:
        raise ValueError(f"Unsupported region: {region}")

    data_enc = aes_cbc_encrypt(raw_payload)
    token, lock, server = await get_token_info(region)
    
    headers = {
        'User-Agent': USERAGENT,
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/octet-stream",
        'Expect': "100-continue",
        'Authorization': token,
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': RELEASEVERSION
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(server + endpoint, data=data_enc, headers=headers, timeout=12.0)
        resp.raise_for_status()

        proto_msg = decode_protobuf(resp.content, response_class)
        try:
            json_str = json_format.MessageToJson(
                proto_msg,
                preserving_proto_field_name=True,
                including_default_value_fields=True
            )
        except TypeError:
            json_str = json_format.MessageToJson(
                proto_msg,
                preserving_proto_field_name=True,
                always_print_fields_with_no_presence=True
            )
        return json.loads(json_str)