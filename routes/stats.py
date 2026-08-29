import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
from proto import PlayerStats_pb2

stats_bp = Blueprint('stats', __name__)

def build_player_stats_payload(uid: int, match_mode: int = 0) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    payload.append(0x10)
    payload.extend(encode_varint(int(match_mode)))
    return bytes(payload)

@stats_bp.route('/stats')
def get_player_stats():
    uid = request.args.get('uid')
    region = request.args.get('region', 'SG').upper()
    match_mode = int(request.args.get('mode', '0')) # 0 = All, 1 = Ranked, 2 = Casual
    
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    try:
        payload = build_player_stats_payload(int(uid), match_mode)
        data = asyncio.run(dispatch_freefire_request(region, "/GetPlayerStats", payload, PlayerStats_pb2.CSGetPlayerStatsRes))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch combat stats: {str(e)}"}), 500