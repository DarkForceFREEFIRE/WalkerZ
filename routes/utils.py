import asyncio
import httpx
from flask import Blueprint, request, jsonify
from core.auth import initialize_tokens, SUPPORTED_REGIONS

utils_bp = Blueprint('utils', __name__)

async def fetch_ban_status(uid: str, lang: str = "en") -> dict:
    url = "https://ff.garena.com/api/antihack/check_banned"
    params = {"lang": lang, "uid": uid}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://ff.garena.com/en/support/",
        "X-Requested-With": "B6FksShzIgjfrYImLpTsadjS86sddhFH",
        "Accept": "application/json, text/plain, */*"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, headers=headers, timeout=10.0)
        resp.raise_for_status()
        return resp.json()

@utils_bp.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Free Fire Info API v2.0",
        "endpoints": {
            "GET /get": {
                "description": "Fetch complete player profile & personal show info",
                "params": "?uid=<player_id>&region=<region_code>",
                "example": "/get?uid=10597688191&region=SG"
            },
            "GET /gallery": {
                "description": "Fetch gallery showcase, social media links & badges",
                "params": "?uid=<player_id>&extra=<true|false>&region=<region_code>",
                "example": "/gallery?uid=10597688191&extra=true&region=SG"
            },
            "GET /wishlist": {
                "description": "Fetch player wishlisted items and release timestamps",
                "params": "?uid=<player_id>&region=<region_code>",
                "example": "/wishlist?uid=10597688191&region=SG"
            },
            "GET /wishlist/leaderboard": {
                "description": "Fetch top wished items leaderboard (7d and 30d)",
                "params": "?region=<region_code>",
                "example": "/wishlist/leaderboard?region=SG"
            },
            "GET /occupation": {
                "description": "Fetch occupation/role masteries, scores & stats",
                "params": "?uid=<player_id>&region=<region_code>",
                "example": "/occupation?uid=10597688191&region=SG"
            },
            "POST /occupation/set_new_season_show": {
                "description": "Update occupation display for new season",
                "params": "?game_mode=<id>&match_mode=<id>&region=<region_code>",
                "example": "/occupation/set_new_season_show?game_mode=1&match_mode=2&region=SG"
            },
            "GET /outfit": {
                "description": "Fetch player's equipped clothes, skills, and custom items",
                "params": "?uid=<player_id>&region=<region_code>",
                "example": "/outfit?uid=10597688191&region=SG"
            },
            "GET /search": {
                "description": "Search player accounts by nickname",
                "params": "?name=<nickname>&region=<region_code>",
                "example": "/search?name=Vortex&region=SG"
            },
            "GET /clan": {
                "description": "Fetch clan/guild details, activeness, and member list",
                "params": "?clan_id=<clan_id>&region=<region_code>",
                "example": "/clan?clan_id=1028000098&region=SG"
            },
            "GET /stats": {
                "description": "Fetch BR lifetime & seasonal combat stats (Solo/Duo/Squad)",
                "params": "?uid=<player_id>&mode=<0=all|1=ranked|2=casual>&region=<region_code>",
                "example": "/stats?uid=10597688191&mode=1&region=SG"
            },
            "GET /cs_stats": {
                "description": "Fetch Clash Squad (CS) detailed stats",
                "params": "?uid=<player_id>&season=<season_id>&mode=<1=ranked|2=casual>&region=<region_code>",
                "example": "/cs_stats?uid=10597688191&season=27&mode=1&region=SG"
            },
            "GET /heroic_history": {
                "description": "Fetch historical Heroic & Grandmaster season badges",
                "params": "?uid=<player_id>&region=<region_code>",
                "example": "/heroic_history?uid=10597688191&region=SG"
            },
            "GET/POST /batch_get": {
                "description": "Bulk fetch profile summaries for multiple UIDs",
                "params": "?uids=<uid1,uid2,uid3>&region=<region_code>",
                "example": "/batch_get?uids=10597688191,1028000098&region=SG"
            },
            "GET /weapon_exp": {
                "description": "Fetch weapon mastery EXP, levels, kills & headshots",
                "params": "?uid=<player_id>&region=<region_code>",
                "example": "/weapon_exp?uid=10597688191&region=SG"
            },
            "GET /weapon_glory": {
                "description": "Fetch weapon power regional leaderboard titles & records",
                "params": "?uid=<player_id>&region=<region_code>",
                "example": "/weapon_glory?uid=10597688191&region=SG"
            },
            "GET /leaderboard": {
                "description": "Fetch regional BR or CS ranked leaderboards",
                "params": "?type=<1=BR|2=CS>&page=<page_num>&size=<page_size>&region=<region_code>",
                "example": "/leaderboard?type=2&page=1&size=50&region=SG"
            },
            "GET /check_ban": {
                "description": "Check anti-hack ban status from official support API",
                "params": "?uid=<player_id>&lang=<language_code>",
                "example": "/check_ban?uid=10597688191&lang=en"
            },
            "GET/POST /refresh": {
                "description": "Manually refresh JWT authentication tokens for all regions",
                "example": "/refresh"
            },
            "GET /get_all": {
                "description": "Fetch all player details (Personal Show, Wishlist, CS Stats, Outfit, Weapon Glory, Occupation, Combat Stats, Heroic History) concurrently",
                "params": "?uid=<player_id>&region=<region_code>",
                "example": "/get_all?uid=10597688191&region=SG"
            }
        },
        "supported_regions": sorted(list(SUPPORTED_REGIONS)),
        "credits": {
            "Backend API and decryption": "Walker"
        }
    })

@utils_bp.route('/check_ban')
def check_ban():
    uid = request.args.get('uid')
    lang = request.args.get('lang', 'en')
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400
    try:
        ban_data = asyncio.run(fetch_ban_status(uid, lang))
        return jsonify(ban_data), 200
    except Exception as e:
        return jsonify({"error": f"Anti-hack check error: {e}"}), 500

@utils_bp.route('/refresh', methods=['GET', 'POST'])
def refresh():
    try:
        asyncio.run(initialize_tokens())
        return jsonify({'message': 'Tokens refreshed for all regions.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500