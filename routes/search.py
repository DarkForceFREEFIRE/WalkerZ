import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
from proto import Search_pb2

search_bp = Blueprint('search', __name__)

def build_fuzzy_search_payload(nickname: str) -> bytes:
    name_bytes = nickname.encode('utf-8')
    payload = bytearray()
    payload.append(0x0A)
    payload.extend(encode_varint(len(name_bytes)))
    payload.extend(name_bytes)
    return bytes(payload)

@search_bp.route('/search')
def search_account_by_name():
    name = request.args.get('name')
    region = request.args.get('region', 'SG').upper()
    if not name:
        return jsonify({"error": "Please provide a name parameter."}), 400

    try:
        payload = build_fuzzy_search_payload(name)
        data = asyncio.run(dispatch_freefire_request(region, "/FuzzySearchAccountByName", payload, Search_pb2.AccountInfoBasicBundleRes))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Search failed on region {region}: {str(e)}"}), 500