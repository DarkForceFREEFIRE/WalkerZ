import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
try:
    from proto import Wishlist_pb2
except ImportError:
    Wishlist_pb2 = None

wishlist_bp = Blueprint('wishlist', __name__)

def build_wishlist_req(uid: int) -> bytes:
    # Field 1: ulong account_id (tag 1, wire type 0 = 0x08)
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    return bytes(payload)

@wishlist_bp.route('/wishlist')
def get_wishlist():
    """Fetch player's wishlist item IDs and release timestamps."""
    uid = request.args.get('uid')
    region = request.args.get('region', 'SG').upper()
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    try:
        payload = build_wishlist_req(int(uid))
        response_type = getattr(Wishlist_pb2, 'CSGetWishListItemsRes', None)
        data = asyncio.run(dispatch_freefire_request(
            region, 
            "/GetWishListItems", 
            payload, 
            response_type
        ))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch wishlist: {str(e)}"}), 500

@wishlist_bp.route('/wishlist/leaderboard')
def get_wishlist_leaderboard():
    """Fetch top trending wished items (7d and 30d)."""
    region = request.args.get('region', 'SG').upper()
    try:
        response_type = getattr(Wishlist_pb2, 'CSGetWishListLeaderboardRes', None)
        data = asyncio.run(dispatch_freefire_request(
            region, 
            "/GetWishListLeaderboard", 
            b"", 
            response_type
        ))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch wishlist leaderboard: {str(e)}"}), 500