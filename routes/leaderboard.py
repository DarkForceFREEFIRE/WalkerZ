# leaderboard.py

import asyncio
from flask import Blueprint, request, jsonify
from core.client import dispatch_freefire_request
from proto import Leaderboard_pb2

leaderboard_bp = Blueprint('leaderboard', __name__)

@leaderboard_bp.route('/leaderboard')
def get_leaderboard():
    main_type = int(request.args.get('type', '1'))  # 1 = BR Ranked, 2 = CS Ranked
    page_index = int(request.args.get('page', '0'))
    page_size = int(request.args.get('size', '50'))
    region = request.args.get('region', 'SG').upper()

    try:
        # Use Protobuf message serialization instead of manual byte packing
        req = Leaderboard_pb2.CSLeaderboardReq(
            main_type=main_type,
            sub_type=0,
            page_index=page_index,
            page_size=page_size,
            get_self=True,
            region=region,
            lock_region=region
        )
        payload = req.SerializeToString()

        data = asyncio.run(
            dispatch_freefire_request(
                region, 
                "/Leaderboard", 
                payload, 
                Leaderboard_pb2.CSLeaderboardRes
            )
        )
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve leaderboard: {str(e)}"}), 500