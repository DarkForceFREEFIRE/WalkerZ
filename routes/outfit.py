import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
try:
    from proto import Outfit_pb2
except ImportError:
    Outfit_pb2 = None

outfit_bp = Blueprint('outfit', __name__)

def build_outfit_req(uid: int) -> bytes:
    # Field 1: ulong account_id (tag 1 = 0x08)
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    return bytes(payload)

@outfit_bp.route('/outfit')
def get_outfit():
    """Fetch player's equipped outfit, clothes, skin accessories, and customizations."""
    uid = request.args.get('uid')
    region = request.args.get('region', 'SG').upper()
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    try:
        payload = build_outfit_req(int(uid))
        response_type = getattr(Outfit_pb2, 'CSGetAccountOutfitRes', None)
        data = asyncio.run(dispatch_freefire_request(
            region, 
            "/GetAccountOutfit", 
            payload, 
            response_type
        ))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch outfit details: {str(e)}"}), 500