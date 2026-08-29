import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from core.crypto import encode_varint
from proto import BatchLookup_pb2

batch_bp = Blueprint('batch', __name__)

def build_batch_lookup_payload(uids: list) -> bytes:
    payload = bytearray()
    # Packed array of uids: Tag 1, wire type 2 (length-delimited)
    uids_bytes = bytearray()
    for uid in uids:
        uids_bytes.extend(encode_varint(int(uid)))
    
    payload.append(0x0A)
    payload.extend(encode_varint(len(uids_bytes)))
    payload.extend(uids_bytes)
    
    # call_sign_src = 7
    payload.append(0x10)
    payload.extend(encode_varint(7))
    return bytes(payload)

@batch_bp.route('/batch_get', methods=['GET', 'POST'])
def batch_get_accounts():
    region = request.args.get('region', 'SG').upper()
    
    if request.method == 'POST':
        body = request.get_json(silent=True) or {}
        uids = body.get('uids', [])
    else:
        raw_uids = request.args.get('uids', '')
        uids = [u.strip() for u in raw_uids.split(',') if u.strip()]

    if not uids:
        return jsonify({"error": "Please provide a list of UIDs."}), 400

    try:
        payload = build_batch_lookup_payload(uids[:50]) # cap at 50 per batch
        data = asyncio.run(dispatch_freefire_request(region, "/BatchGetAccountInfo", payload, BatchLookup_pb2.CSBatchGetAccountInfoRes))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Batch lookup failed: {str(e)}"}), 500