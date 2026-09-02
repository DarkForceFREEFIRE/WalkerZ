import os
import sys

# Path resolution for protobuf imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'proto')))

import logging
from flask import Flask
from flask_cors import CORS

from routes.player import player_bp
from routes.search import search_bp
from routes.clan import clan_bp
from routes.weapon_glory import weapon_glory_bp
from routes.stats import stats_bp
from routes.cs_stats import cs_stats_bp
from routes.heroic import heroic_bp
from routes.batch import batch_bp
from routes.leaderboard import leaderboard_bp
from routes.weapon_exp import weapon_exp_bp
from routes.wishlist import wishlist_bp
from routes.occupation import occupation_bp
from routes.gallery import gallery_bp
from routes.outfit import outfit_bp
from routes.utils import utils_bp
from routes.full_info import full_info_bp

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

app.register_blueprint(player_bp)
app.register_blueprint(search_bp)
app.register_blueprint(clan_bp)
app.register_blueprint(weapon_glory_bp)
app.register_blueprint(stats_bp)
app.register_blueprint(cs_stats_bp)
app.register_blueprint(heroic_bp)
app.register_blueprint(batch_bp)
app.register_blueprint(weapon_exp_bp)
app.register_blueprint(leaderboard_bp)
app.register_blueprint(wishlist_bp)
app.register_blueprint(occupation_bp)
app.register_blueprint(gallery_bp)
app.register_blueprint(outfit_bp)
app.register_blueprint(utils_bp)
app.register_blueprint(full_info_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)