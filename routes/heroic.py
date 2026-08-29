import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
from proto import HeroicInfo_pb2

heroic_bp = Blueprint('heroic', __name__)

def build_heroic_payload(uid: int) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    payload.append(0x10)
    payload.append(0x01) # need_max_rank = True
    return bytes(payload)

@heroic_bp.route('/heroic_history')
def get_heroic_history():
    uid = request.args.get('uid')
    region = request.args.get('region', 'SG').upper()
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    try:
        payload = build_heroic_payload(int(uid))
        data = asyncio.run(dispatch_freefire_request(region, "/GetHeroicInfo", payload, HeroicInfo_pb2.CSGetHeroicInfoRes))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch heroic history: {str(e)}"}), 500