import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
from core.auth import SUPPORTED_REGIONS

# Protobuf imports with safe fallbacks
try:
    from proto import AccountPersonalShow_pb2
except ImportError:
    AccountPersonalShow_pb2 = None

try:
    from proto import Wishlist_pb2
except ImportError:
    Wishlist_pb2 = None

try:
    from proto import CSStats_pb2
except ImportError:
    CSStats_pb2 = None

try:
    from proto import Outfit_pb2
except ImportError:
    Outfit_pb2 = None

try:
    from proto import WeaponPower_pb2
except ImportError:
    WeaponPower_pb2 = None

try:
    from proto import Occupation_pb2
except ImportError:
    Occupation_pb2 = None

try:
    from proto import PlayerStats_pb2
except ImportError:
    PlayerStats_pb2 = None

try:
    from proto import HeroicInfo_pb2
except ImportError:
    HeroicInfo_pb2 = None

full_info_bp = Blueprint('full_info', __name__)

# --- Payload Builders ---

def build_personal_show_payload(uid: int, call_sign_src: int = 7) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    payload.append(0x10)
    payload.extend(encode_varint(int(call_sign_src)))
    payload.extend([0x18, 0x01, 0x20, 0x01, 0x28, 0x01, 0x30, 0x01])
    return bytes(payload)

def build_wishlist_payload(uid: int) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    return bytes(payload)

def build_cs_stats_payload(uid: int, season_id: int = 0, match_mode: int = 6) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    payload.append(0x10)
    payload.extend(encode_varint(int(season_id)))
    payload.append(0x18)
    payload.extend(encode_varint(15))  # Game mode: 15 = Clash Squad
    payload.append(0x20)
    payload.extend(encode_varint(int(match_mode)))
    return bytes(payload)

def build_outfit_payload(uid: int) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    return bytes(payload)

def build_weapon_glory_payload(uid: int) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    return bytes(payload)

def build_occupation_payload(uid: int) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    return bytes(payload)

def build_player_stats_payload(uid: int, match_mode: int = 0) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    payload.append(0x10)
    payload.extend(encode_varint(int(match_mode)))
    return bytes(payload)

def build_heroic_payload(uid: int) -> bytes:
    payload = bytearray()
    payload.append(0x08)
    payload.extend(encode_varint(int(uid)))
    payload.append(0x10)
    payload.append(0x01)
    return bytes(payload)

# --- Async Aggregator ---

async def fetch_all_player_data(uid: int, region: str) -> dict:
    tasks = {
        "personal_show": dispatch_freefire_request(
            region, 
            "/GetPlayerPersonalShow", 
            build_personal_show_payload(uid), 
            getattr(AccountPersonalShow_pb2, 'AccountPersonalShowInfo', None)
        ),
        "wishlist": dispatch_freefire_request(
            region, 
            "/GetWishListItems", 
            build_wishlist_payload(uid), 
            getattr(Wishlist_pb2, 'CSGetWishListItemsRes', None)
        ),
        "cs_stats": dispatch_freefire_request(
            region, 
            "/GetPlayerTCStats", 
            build_cs_stats_payload(uid, season_id=0, match_mode=6), 
            getattr(CSStats_pb2, 'CSGetPlayerTCStatsRes', None)
        ),
        "outfit": dispatch_freefire_request(
            region, 
            "/GetAccountOutfit", 
            build_outfit_payload(uid), 
            getattr(Outfit_pb2, 'CSGetAccountOutfitRes', None)
        ),
        "weapon_glory": dispatch_freefire_request(
            region, 
            "/GetAccountWeaponPowerTitleRecord", 
            build_weapon_glory_payload(uid), 
            getattr(WeaponPower_pb2, 'CSGetAccountWeaponPowerTitleRecordRes', None)
        ),
        "occupation": dispatch_freefire_request(
            region, 
            "/QueryOccupationDetail", 
            build_occupation_payload(uid), 
            getattr(Occupation_pb2, 'CSQueryOccupationDetailRes', None)
        ),
        "stats": dispatch_freefire_request(
            region, 
            "/GetPlayerStats", 
            build_player_stats_payload(uid, match_mode=0), 
            getattr(PlayerStats_pb2, 'CSGetPlayerStatsRes', None)
        ),
        "heroic_history": dispatch_freefire_request(
            region, 
            "/GetHeroicInfo", 
            build_heroic_payload(uid), 
            getattr(HeroicInfo_pb2, 'CSGetHeroicInfoRes', None)
        )
    }

    # Execute all requests simultaneously
    keys = list(tasks.keys())
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    bundled_data = {}
    for key, result in zip(keys, results):
        if isinstance(result, Exception):
            bundled_data[key] = {"error": str(result)}
        else:
            bundled_data[key] = result

    return bundled_data

@full_info_bp.route('/get_all')
def get_all_player_info():
    """Fetches full player profile, wishlist, CS stats, outfit, weapon glory, occupation, stats, and heroic history in parallel."""
    uid = request.args.get('uid')
    region = request.args.get('region')

    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    try:
        uid_int = int(uid)
    except ValueError:
        return jsonify({"error": "Invalid UID format. UID must be an integer."}), 400

    if region:
        region = region.strip().upper()

    # Auto region detection if not provided or set to AUTO
    if not region or region == "AUTO" or region not in SUPPORTED_REGIONS:
        detected_region = None
        for reg in SUPPORTED_REGIONS:
            try:
                # Test with personal show first to find the valid region
                test_payload = build_personal_show_payload(uid_int)
                asyncio.run(dispatch_freefire_request(
                    reg, 
                    "/GetPlayerPersonalShow", 
                    test_payload, 
                    getattr(AccountPersonalShow_pb2, 'AccountPersonalShowInfo', None)
                ))
                detected_region = reg
                break
            except Exception:
                continue

        if not detected_region:
            return jsonify({"error": "UID not found in any supported region."}), 404
        region = detected_region

    try:
        data = asyncio.run(fetch_all_player_data(uid_int, region))
        return jsonify({
            "uid": uid_int,
            "region": region,
            "data": data
        }), 200, {'X-Selected-Region': region}
    except Exception as e:
        return jsonify({"error": f"Failed to fetch full account bundle: {str(e)}"}), 500