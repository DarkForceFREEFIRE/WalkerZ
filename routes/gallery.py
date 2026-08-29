import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
try:
    from proto import Gallery_pb2
except ImportError:
    Gallery_pb2 = None

gallery_bp = Blueprint('gallery', __name__)

def build_gallery_info_req(uid: int, is_extra: bool = True, token: str = "") -> bytes:
    # Field 1: ulong account_id (tag 1 = 0x08)
    # Field 2: bool is_extra (tag 2 = 0x10)
    # Field 3: string access_token (tag 3, wire type 2 = 0x1A)
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    payload.append(0x10)
    payload.append(1 if is_extra else 0)
    if token:
        payload.append(0x1A)
        token_bytes = token.encode('utf-8')
        payload.extend(encode_varint(len(token_bytes)))
        payload.extend(token_bytes)
    return bytes(payload)

@gallery_bp.route('/gallery')
def get_player_gallery():
    """Fetch gallery showcase, linked social media profiles, and achievements."""
    uid = request.args.get('uid')
    is_extra = request.args.get('extra', 'true').lower() == 'true'
    region = request.args.get('region', 'SG').upper()
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    try:
        payload = build_gallery_info_req(int(uid), is_extra=is_extra)
        response_type = getattr(Gallery_pb2, 'CSGetPlayerGalleryInfoSettingRes', None)
        data = asyncio.run(dispatch_freefire_request(
            region, 
            "/GetPlayerGalleryInfoSetting", 
            payload, 
            response_type
        ))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch gallery show info: {str(e)}"}), 500