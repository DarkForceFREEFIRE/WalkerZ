import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
from core.auth import SUPPORTED_REGIONS
from proto import AccountPersonalShow_pb2

player_bp = Blueprint('player', __name__)

def build_raw_personal_show_payload(uid: int, call_sign_src: int = 7) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    payload.append(0x10)
    payload.extend(encode_varint(int(call_sign_src)))
    payload.extend([0x18, 0x01, 0x20, 0x01, 0x28, 0x01, 0x30, 0x01])
    return bytes(payload)

def extract_account_details(data):
    """
    Safely extract nickname and show_emulator_flag (as 0 or 1)
    whether data is a dict or a protobuf object.
    """
    nickname = None
    is_emulator = 0

    if isinstance(data, dict):
        basic_info = data.get("basic_info") or {}
        nickname = basic_info.get("nickname")
        is_emulator = 1 if basic_info.get("show_emulator_flag") else 0
    elif hasattr(data, "basic_info"):
        basic_info = getattr(data, "basic_info", None)
        if basic_info:
            nickname = getattr(basic_info, "nickname", None)
            is_emulator = 1 if getattr(basic_info, "show_emulator_flag", False) else 0

    return nickname, is_emulator

@player_bp.route('/get')
def get_account_info():
    region = request.args.get('region')
    uid = request.args.get('uid')
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    if region:
        region = region.strip().upper()

    if not region or region == "AUTO" or region not in SUPPORTED_REGIONS:
        for reg in SUPPORTED_REGIONS:
            try:
                payload = build_raw_personal_show_payload(int(uid))
                data = asyncio.run(dispatch_freefire_request(reg, "/GetPlayerPersonalShow", payload, AccountPersonalShow_pb2.AccountPersonalShowInfo))
                return jsonify(data), 200, {'X-Detected-Region': reg}
            except Exception:
                continue
        return jsonify({"error": "UID not found in any supported region."}), 404

    try:
        payload = build_raw_personal_show_payload(int(uid))
        data = asyncio.run(dispatch_freefire_request(region, "/GetPlayerPersonalShow", payload, AccountPersonalShow_pb2.AccountPersonalShowInfo))
        return jsonify(data), 200, {'X-Selected-Region': region}
    except Exception as e:
        return jsonify({"error": f"Invalid UID or Region ({region}). Details: {str(e)}"}), 500

@player_bp.route('/nickname')
def get_account_nickname():
    region = request.args.get('region')
    uid = request.args.get('uid')
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    if region:
        region = region.strip().upper()

    # Auto-detect region if not specified or invalid
    if not region or region == "AUTO" or region not in SUPPORTED_REGIONS:
        for reg in SUPPORTED_REGIONS:
            try:
                payload = build_raw_personal_show_payload(int(uid))
                data = asyncio.run(
                    dispatch_freefire_request(
                        reg, 
                        "/GetPlayerPersonalShow", 
                        payload, 
                        AccountPersonalShow_pb2.AccountPersonalShowInfo
                    )
                )
                nickname, is_emulator = extract_account_details(data)
                if nickname:
                    return jsonify({
                        "uid": int(uid),
                        "nickname": nickname,
                        "emulator": is_emulator,
                        "region": reg
                    }), 200, {'X-Detected-Region': reg}
            except Exception:
                continue
        return jsonify({"error": "UID not found in any supported region."}), 404

    # Targeted region query
    try:
        payload = build_raw_personal_show_payload(int(uid))
        data = asyncio.run(
            dispatch_freefire_request(
                region, 
                "/GetPlayerPersonalShow", 
                payload, 
                AccountPersonalShow_pb2.AccountPersonalShowInfo
            )
        )
        nickname, is_emulator = extract_account_details(data)
        if not nickname:
            return jsonify({"error": "Nickname not found for this UID."}), 404

        return jsonify({
            "uid": int(uid),
            "nickname": nickname,
            "emulator": is_emulator,
            "region": region
        }), 200, {'X-Selected-Region': region}
    except Exception as e:
        return jsonify({"error": f"Invalid UID or Region ({region}). Details: {str(e)}"}), 500
