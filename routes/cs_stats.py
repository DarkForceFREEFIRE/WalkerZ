import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
from proto import CSStats_pb2

cs_stats_bp = Blueprint('cs_stats', __name__)

def build_cs_stats_payload(uid: int, season_id: int = 0, match_mode: int = 6) -> bytes:
    """
    Constructs CSGetPlayerTCStatsReq (TypeDefIndex: 7078):
    Tag 1: account_id (uid)
    Tag 2: season_id (0 = lifetime, or specific season number)
    Tag 3: game_mode (15 = Clash Squad)
    Tag 4: match_mode (6 = Ranked, 1 = Normal/Casual, 0 = Career/All)
    """
    payload = bytearray()
    
    # Tag 1: account_id
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    
    # Tag 2: season_id
    payload.append(0x10)
    payload.extend(encode_varint(int(season_id)))
    
    # Tag 3: game_mode = 15 (CS)
    payload.append(0x18)
    payload.extend(encode_varint(15))
    
    # Tag 4: match_mode (6 = Ranked, 1 = Casual, 0 = All)
    payload.append(0x20)
    payload.extend(encode_varint(int(match_mode)))
    
    return bytes(payload)

@cs_stats_bp.route('/cs_stats')
def get_cs_stats():
    uid = request.args.get('uid')
    region = request.args.get('region', 'SG').upper()
    season_id = int(request.args.get('season', '0'))
    
    # mode mapping: "ranked" -> 6, "casual"/"normal" -> 1, "all"/"career" -> 0
    mode_param = request.args.get('mode', 'ranked').lower()
    if mode_param in ['ranked', '6']:
        match_mode = 6
    elif mode_param in ['casual', 'normal', '1']:
        match_mode = 1
    else:
        match_mode = 0

    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    try:
        payload = build_cs_stats_payload(int(uid), season_id=season_id, match_mode=match_mode)
        data = asyncio.run(dispatch_freefire_request(
            region=region,
            endpoint="/GetPlayerTCStats",
            raw_payload=payload,
            response_class=CSStats_pb2.CSGetPlayerTCStatsRes
        ))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch Clash Squad stats: {str(e)}"}), 500