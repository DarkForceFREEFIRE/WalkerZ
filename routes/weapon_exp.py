import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
from proto import WeaponExp_pb2

weapon_exp_bp = Blueprint('weapon_exp', __name__)

def build_weapon_exp_payload(uid: int) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    return bytes(payload)

@weapon_exp_bp.route('/weapon_exp')
def get_weapon_exp():
    uid = request.args.get('uid')
    region = request.args.get('region', 'SG').upper()
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    try:
        payload = build_weapon_exp_payload(int(uid))
        data = asyncio.run(dispatch_freefire_request(region, "/GetAccountWeaponExpInfo", payload, WeaponExp_pb2.CSGetAccountWeaponExpInfoRes))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch weapon exp: {str(e)}"}), 500