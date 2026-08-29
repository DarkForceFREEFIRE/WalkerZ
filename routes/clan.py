import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
from proto import Clan_pb2

clan_bp = Blueprint('clan', __name__)

def build_clan_info_payload(clan_id: int, need_members: bool = True) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(clan_id)))
    payload.append(0x10)
    payload.append(0x01 if need_members else 0x00)
    return bytes(payload)

@clan_bp.route('/clan')
def get_clan_info():
    clan_id = request.args.get('clan_id')
    region = request.args.get('region', 'SG').upper()
    if not clan_id:
        return jsonify({"error": "Please provide clan_id."}), 400

    try:
        payload = build_clan_info_payload(int(clan_id))
        data = asyncio.run(dispatch_freefire_request(region, "/GetClanMainPageInfo", payload, Clan_pb2.CSGetClanMainPageInfoRes))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Clan lookup failed on {region}: {str(e)}"}), 500