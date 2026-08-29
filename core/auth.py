import time
import httpx
import json
import logging
from collections import defaultdict
from typing import Tuple

SUPPORTED_REGIONS = {"SG", "IND", "BR", "US", "SAC", "NA", "RU", "ID", "TW", "VN", "TH", "ME", "PK", "BD"}
ACCOUNTS_BY_REGION = {}

try:
    with open('accounts.json', 'r', encoding='utf-8') as f:
        accounts_data = json.load(f)
        for entry in accounts_data:
            region = entry.get('region', '').upper()
            if region and region in SUPPORTED_REGIONS:
                ACCOUNTS_BY_REGION[region] = {
                    'uid': entry['uid'],
                    'password': entry['password']
                }
except Exception as e:
    logging.error(f"Error loading accounts.json: {e}")

cached_tokens = defaultdict(dict)

def get_account_credentials(region: str) -> Tuple[str, str]:
    r = region.upper()
    if r in ACCOUNTS_BY_REGION:
        creds = ACCOUNTS_BY_REGION[r]
        return creds['uid'], creds['password']
    return "3937206629", "E4D17A3799816184A9BA20C68D8DE55C69180F8C793CA1C6B164C6D14848D8DF"

async def fetch_jwt_from_external_api(uid: str, password: str) -> dict:
    url = "https://wzjwt.vercel.app/api/process"
    params = {"mode": "id_pass", "uid": uid, "password": password}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            raise Exception(f"External API error: {data.get('message', 'Unknown error')}")
        return data

async def create_jwt(region: str):
    uid, password = get_account_credentials(region)
    data = await fetch_jwt_from_external_api(uid, password)
    jwt = data.get("jwt")
    lock_region = data.get("lockRegion", region)
    server_url = data.get("serverUrl")
    if not jwt or not server_url:
        raise Exception("Missing jwt or serverUrl in API response")
    cached_tokens[region] = {
        'token': f"Bearer {jwt}",
        'region': lock_region,
        'server_url': server_url,
        'expires_at': time.time() + 25200
    }

async def get_token_info(region: str) -> Tuple[str, str, str]:
    info = cached_tokens.get(region)
    if info and time.time() < info['expires_at']:
        return info['token'], info['region'], info['server_url']
    await create_jwt(region)
    info = cached_tokens[region]
    return info['token'], info['region'], info['server_url']

async def initialize_tokens():
    tasks = [create_jwt(r) for r in SUPPORTED_REGIONS]
    import asyncio
    await asyncio.gather(*tasks, return_exceptions=True)