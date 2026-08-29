import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
from proto import WeaponPower_pb2

weapon_glory_bp = Blueprint('weapon_glory', __name__)

def build_weapon_power_payload(uid: int) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    return bytes(payload)

@weapon_glory_bp.route('/weapon_glory')
def get_weapon_glory():
    uid = request.args.get('uid')
    region = request.args.get('region', 'SG').upper()
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    try:
        payload = build_weapon_power_payload(int(uid))
        data = asyncio.run(dispatch_freefire_request(region, "/GetAccountWeaponPowerTitleRecord", payload, WeaponPower_pb2.CSGetAccountWeaponPowerTitleRecordRes))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Weapon glory lookup failed: {str(e)}"}), 500