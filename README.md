# Walker Regedits Free Fire API
🌸 The most powerful Free Fire info API

# OSP Developer Notes

This file is for OSP/dev integration work. It is intentionally compact and machine-friendly.

## API base

Use a single base variable in your code:

```python
BASE_URL = "https://wzapi.vercel.app"
```

Do not hardcode `http://127.0.0.1:5000` in prod or shared examples.

---

## Flask app wiring

Routes are registered in [app.py](app.py):

```python
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
```

The service is a Flask app run with:

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

---

## Endpoint contract summary

```yaml
GET /check_ban:
  required: [uid]
  optional: [lang]
  default_lang: en

GET /get:
  required: [uid]
  optional: [region]
  default_region: SG

GET /search:
  required: [name]
  optional: [region]
  default_region: SG

GET /stats:
  required: [uid]
  optional: [mode, region]
  mode_values: {0: all, 1: ranked, 2: casual}

GET /wishlist:
  required: [uid]
  optional: [region]

GET /wishlist/leaderboard:
  required: [region]

GET /occupation:
  required: [uid]
  optional: [region]

POST /occupation/set_new_season_show:
  required: [game_mode, match_mode]
  optional: [region]

GET /outfit:
  required: [uid]
  optional: [region]

GET /clan:
  required: [clan_id]
  optional: [region]

GET /cs_stats:
  required: [uid]
  optional: [season, mode, region]
  mode_values: {1: ranked, 2: casual}

GET /heroic_history:
  required: [uid]
  optional: [region]

GET /batch_get:
  required: [uids]
  optional: [region]
  uids_format: comma-separated integers

GET /weapon_exp:
  required: [uid]
  optional: [region]

GET /weapon_glory:
  required: [uid]
  optional: [region]

GET /leaderboard:
  required: [type]
  optional: [page, size, region]
  type_values: {1: BR, 2: CS}

POST /refresh:
  required: []
  optional: []
```

---

## Example requests

```bash
BASE_URL="https://wzapi.vercel.app"

curl -G "$BASE_URL/get" \
  --data-urlencode "uid=10597688191" \
  --data-urlencode "region=SG"

curl -G "$BASE_URL/stats" \
  --data-urlencode "uid=10597688191" \
  --data-urlencode "mode=1" \
  --data-urlencode "region=SG"

curl -G "$BASE_URL/wishlist/leaderboard" \
  --data-urlencode "region=SG"

curl -X POST "$BASE_URL/occupation/set_new_season_show?game_mode=1&match_mode=2&region=SG"

curl -X POST "$BASE_URL/refresh"
```

---

## OSP implementation notes

- The app uses Flask blueprints, so each route module is separate in the `routes/` folder.
- Requests are usually query-string based, not JSON-body heavy.
- Keep `region` handling consistent with the API default (`SG`) unless the caller explicitly overrides it.
- For batch requests, pass a comma-separated UID list and validate IDs before querying.
- For auth/refresh flow, treat `/refresh` as maintenance or token renewal logic, not a normal business endpoint.

## Route modules

```text
routes/
  batch.py
  clan.py
  cs_stats.py
  gallery.py
  heroic.py
  leaderboard.py
  occupation.py
  outfit.py
  player.py
  search.py
  stats.py
  utils.py
  weapon_exp.py
  weapon_glory.py
  wishlist.py
```

## Runtime

```bash
python app.py
```

This runs the app on port 5000 with debug enabled in local development.
