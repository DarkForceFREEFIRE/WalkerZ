import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
try:
    from proto import Occupation_pb2
except ImportError:
    Occupation_pb2 = None

occupation_bp = Blueprint('occupation', __name__)

def build_occupation_detail_req(uid: int) -> bytes:
    # Field 1: ulong account_id (tag 1, wire type 0 = 0x08)
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    return bytes(payload)

def build_set_new_season_show_req(game_mode: int, match_mode: int) -> bytes:
    # Field 1: uint game_mode (tag 1 = 0x08)
    # Field 2: uint match_mode (tag 2 = 0x10)
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(game_mode)))
    payload.append(0x10)
    payload.extend(encode_varint(int(match_mode)))
    return bytes(payload)

@occupation_bp.route('/occupation')
def get_occupation_detail():
    """Fetch role/occupation proficiency, weapons usage, scores and season records."""
    uid = request.args.get('uid')
    region = request.args.get('region', 'SG').upper()
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    try:
        payload = build_occupation_detail_req(int(uid))
        response_type = getattr(Occupation_pb2, 'CSQueryOccupationDetailRes', None)
        data = asyncio.run(dispatch_freefire_request(
            region, 
            "/QueryOccupationDetail", 
            payload, 
            response_type
        ))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to query occupation detail: {str(e)}"}), 500

@occupation_bp.route('/occupation/set_new_season_show', methods=['POST', 'GET'])
def set_occupation_new_season_show():
    """Update new season display flag for occupations."""
    game_mode = request.args.get('game_mode', request.json.get('game_mode') if request.is_json else None)
    match_mode = request.args.get('match_mode', request.json.get('match_mode') if request.is_json else None)
    region = request.args.get('region', 'SG').upper()

    if game_mode is None or match_mode is None:
        return jsonify({"error": "Please provide both 'game_mode' and 'match_mode'."}), 400

    try:
        payload = build_set_new_season_show_req(int(game_mode), int(match_mode))
        data = asyncio.run(dispatch_freefire_request(
            region, 
            "/SetOccupationNewSeasonShow", 
            payload, 
            None
        ))
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to set occupation new season show: {str(e)}"}), 500