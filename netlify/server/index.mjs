// Netlify Server entrypoint: Free Fire Info API (port of the original Flask app).
import { Hono } from 'hono'
import { cors } from 'hono/cors'

import endpoints from '../../src/endpoints.json' with { type: 'json' }
import {
  SUPPORTED_REGIONS,
  buildPayload,
  dispatchFreefireRequest,
  initializeTokens,
  lookupType,
} from '../../src/freefire.mjs'

const app = new Hono()
app.use('*', cors())

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const isInt = (v) => typeof v === 'string' && /^\s*-?\d+\s*$/.test(v)
const errMsg = (e) => (e instanceof Error ? e.message : String(e))

/** Region query param, upper-cased, defaulting to SG. */
const regionParam = (c) => (c.req.query('region') || 'SG').toUpperCase()

const payloads = {
  personalShow: (uid) =>
    Buffer.concat([
      buildPayload([[1, 'varint', uid], [2, 'varint', 7]]),
      Buffer.from([0x18, 0x01, 0x20, 0x01, 0x28, 0x01, 0x30, 0x01]),
    ]),
  uidOnly: (uid) => buildPayload([[1, 'varint', uid]]),
  csStats: (uid, season = 0, matchMode = 6) =>
    buildPayload([[1, 'varint', uid], [2, 'varint', season], [3, 'varint', 15], [4, 'varint', matchMode]]),
  playerStats: (uid, matchMode = 0) => buildPayload([[1, 'varint', uid], [2, 'varint', matchMode]]),
  heroic: (uid) => buildPayload([[1, 'varint', uid], [2, 'varint', 1]]),
}

const getPersonalShow = (region, uid) =>
  dispatchFreefireRequest(region, '/GetPlayerPersonalShow', payloads.personalShow(uid), 'AccountPersonalShowInfo')

/**
 * Query every supported region at once and return the first region (in a stable
 * order) that answered successfully, preferring answers that contain a player.
 */
async function detectRegion(uid) {
  const regions = [...SUPPORTED_REGIONS]
  const results = await Promise.allSettled(regions.map((r) => getPersonalShow(r, uid)))
  let fallback = null
  for (let i = 0; i < regions.length; i++) {
    const res = results[i]
    if (res.status !== 'fulfilled') continue
    if (res.value?.basic_info?.nickname) return { region: regions[i], data: res.value }
    fallback ??= { region: regions[i], data: res.value }
  }
  return fallback
}

const needsDetection = (region) => !region || region === 'AUTO' || !SUPPORTED_REGIONS.has(region)

/** Simple "uid + region -> one game endpoint" route. */
function uidRoute(path, endpoint, responseType, label, buildReq = payloads.uidOnly) {
  app.get(path, async (c) => {
    const uid = c.req.query('uid')
    const region = regionParam(c)
    if (!uid) return c.json({ error: 'Please provide UID.' }, 400)
    if (!isInt(uid)) return c.json({ error: `${label}: invalid UID` }, 500)
    try {
      return c.json(await dispatchFreefireRequest(region, endpoint, buildReq(uid.trim()), responseType))
    } catch (e) {
      return c.json({ error: `${label}: ${errMsg(e)}` }, 500)
    }
  })
}

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

app.get('/', (c) =>
  c.json({
    status: 'online',
    message: 'Free Fire Info API v2.0',
    endpoints,
    supported_regions: [...SUPPORTED_REGIONS].sort(),
    credits: { 'Backend API and decryption': 'Walker' },
  }),
)

app.get('/get', async (c) => {
  const uid = c.req.query('uid')
  const region = c.req.query('region')?.trim().toUpperCase()
  if (!uid) return c.json({ error: 'Please provide UID.' }, 400)
  if (!isInt(uid)) return c.json({ error: 'Invalid UID format. UID must be an integer.' }, 400)

  if (needsDetection(region)) {
    const found = await detectRegion(uid.trim())
    if (!found) return c.json({ error: 'UID not found in any supported region.' }, 404)
    c.header('X-Detected-Region', found.region)
    return c.json(found.data)
  }
  try {
    const data = await getPersonalShow(region, uid.trim())
    c.header('X-Selected-Region', region)
    return c.json(data)
  } catch (e) {
    return c.json({ error: `Invalid UID or Region (${region}). Details: ${errMsg(e)}` }, 500)
  }
})

app.get('/nickname', async (c) => {
  const uid = c.req.query('uid')
  const region = c.req.query('region')?.trim().toUpperCase()
  if (!uid) return c.json({ error: 'Please provide UID.' }, 400)
  if (!isInt(uid)) return c.json({ error: 'Invalid UID format. UID must be an integer.' }, 400)

  const summary = (data, reg) => ({
    uid: Number(uid),
    nickname: data?.basic_info?.nickname,
    emulator: data?.basic_info?.show_emulator_flag ? 1 : 0,
    region: reg,
  })

  if (needsDetection(region)) {
    const found = await detectRegion(uid.trim())
    if (!found?.data?.basic_info?.nickname) {
      return c.json({ error: 'UID not found in any supported region.' }, 404)
    }
    c.header('X-Detected-Region', found.region)
    return c.json(summary(found.data, found.region))
  }
  try {
    const data = await getPersonalShow(region, uid.trim())
    if (!data?.basic_info?.nickname) return c.json({ error: 'Nickname not found for this UID.' }, 404)
    c.header('X-Selected-Region', region)
    return c.json(summary(data, region))
  } catch (e) {
    return c.json({ error: `Invalid UID or Region (${region}). Details: ${errMsg(e)}` }, 500)
  }
})

app.get('/get_all', async (c) => {
  const uid = c.req.query('uid')
  let region = c.req.query('region')?.trim().toUpperCase()
  if (!uid) return c.json({ error: 'Please provide UID.' }, 400)
  if (!isInt(uid)) return c.json({ error: 'Invalid UID format. UID must be an integer.' }, 400)
  const id = uid.trim()

  if (needsDetection(region)) {
    const found = await detectRegion(id)
    if (!found) return c.json({ error: 'UID not found in any supported region.' }, 404)
    region = found.region
  }

  const tasks = {
    personal_show: ['/GetPlayerPersonalShow', payloads.personalShow(id), 'AccountPersonalShowInfo'],
    wishlist: ['/GetWishListItems', payloads.uidOnly(id), 'CSGetWishListItemsRes'],
    cs_stats: ['/GetPlayerTCStats', payloads.csStats(id, 0, 6), 'CSGetPlayerTCStatsRes'],
    outfit: ['/GetAccountOutfit', payloads.uidOnly(id), 'CSGetAccountOutfitRes'],
    weapon_glory: ['/GetAccountWeaponPowerTitleRecord', payloads.uidOnly(id), 'CSGetAccountWeaponPowerTitleRecordRes'],
    occupation: ['/QueryOccupationDetail', payloads.uidOnly(id), 'CSQueryOccupationDetailRes'],
    stats: ['/GetPlayerStats', payloads.playerStats(id, 0), 'CSGetPlayerStatsRes'],
    heroic_history: ['/GetHeroicInfo', payloads.heroic(id), 'CSGetHeroicInfoRes'],
  }
  const keys = Object.keys(tasks)
  const results = await Promise.allSettled(
    keys.map((k) => dispatchFreefireRequest(region, ...tasks[k])),
  )
  const data = {}
  keys.forEach((k, i) => {
    const r = results[i]
    data[k] = r.status === 'fulfilled' ? r.value : { error: errMsg(r.reason) }
  })
  c.header('X-Selected-Region', region)
  return c.json({ uid: Number(id), region, data })
})

app.get('/search', async (c) => {
  const name = c.req.query('name')
  const region = regionParam(c)
  if (!name) return c.json({ error: 'Please provide a name parameter.' }, 400)
  try {
    const payload = buildPayload([[1, 'string', name]])
    return c.json(await dispatchFreefireRequest(region, '/FuzzySearchAccountByName', payload, 'AccountInfoBasicBundleRes'))
  } catch (e) {
    return c.json({ error: `Search failed on region ${region}: ${errMsg(e)}` }, 500)
  }
})

app.get('/clan', async (c) => {
  const clanId = c.req.query('clan_id')
  const region = regionParam(c)
  if (!clanId) return c.json({ error: 'Please provide clan_id.' }, 400)
  try {
    if (!isInt(clanId)) throw new Error('invalid clan_id')
    const payload = buildPayload([[1, 'varint', clanId.trim()], [2, 'varint', 1]])
    return c.json(await dispatchFreefireRequest(region, '/GetClanMainPageInfo', payload, 'CSGetClanMainPageInfoRes'))
  } catch (e) {
    return c.json({ error: `Clan lookup failed on ${region}: ${errMsg(e)}` }, 500)
  }
})

app.get('/stats', async (c) => {
  const uid = c.req.query('uid')
  const region = regionParam(c)
  const mode = c.req.query('mode') ?? '0' // 0 = All, 1 = Ranked, 2 = Casual
  if (!uid) return c.json({ error: 'Please provide UID.' }, 400)
  try {
    if (!isInt(uid) || !isInt(mode)) throw new Error('invalid uid or mode')
    const payload = payloads.playerStats(uid.trim(), mode.trim())
    return c.json(await dispatchFreefireRequest(region, '/GetPlayerStats', payload, 'CSGetPlayerStatsRes'))
  } catch (e) {
    return c.json({ error: `Failed to fetch combat stats: ${errMsg(e)}` }, 500)
  }
})

app.get('/cs_stats', async (c) => {
  const uid = c.req.query('uid')
  const region = regionParam(c)
  const season = c.req.query('season') ?? '0'
  const modeParam = (c.req.query('mode') ?? 'ranked').toLowerCase()
  const matchMode = ['ranked', '6'].includes(modeParam) ? 6 : ['casual', 'normal', '1'].includes(modeParam) ? 1 : 0
  if (!uid) return c.json({ error: 'Please provide UID.' }, 400)
  try {
    if (!isInt(uid) || !isInt(season)) throw new Error('invalid uid or season')
    const payload = payloads.csStats(uid.trim(), season.trim(), matchMode)
    return c.json(await dispatchFreefireRequest(region, '/GetPlayerTCStats', payload, 'CSGetPlayerTCStatsRes'))
  } catch (e) {
    return c.json({ error: `Failed to fetch Clash Squad stats: ${errMsg(e)}` }, 500)
  }
})

uidRoute('/heroic_history', '/GetHeroicInfo', 'CSGetHeroicInfoRes', 'Failed to fetch heroic history', payloads.heroic)
uidRoute('/weapon_exp', '/GetAccountWeaponExpInfo', 'CSGetAccountWeaponExpInfoRes', 'Failed to fetch weapon exp')
uidRoute('/weapon_glory', '/GetAccountWeaponPowerTitleRecord', 'CSGetAccountWeaponPowerTitleRecordRes', 'Weapon glory lookup failed')
uidRoute('/wishlist', '/GetWishListItems', 'CSGetWishListItemsRes', 'Failed to fetch wishlist')
uidRoute('/occupation', '/QueryOccupationDetail', 'CSQueryOccupationDetailRes', 'Failed to query occupation detail')
uidRoute('/outfit', '/GetAccountOutfit', 'CSGetAccountOutfitRes', 'Failed to fetch outfit details')

app.get('/gallery', async (c) => {
  const uid = c.req.query('uid')
  const isExtra = (c.req.query('extra') ?? 'true').toLowerCase() === 'true'
  const region = regionParam(c)
  if (!uid) return c.json({ error: 'Please provide UID.' }, 400)
  try {
    if (!isInt(uid)) throw new Error('invalid uid')
    const payload = buildPayload([[1, 'varint', uid.trim()], [2, 'varint', isExtra ? 1 : 0]])
    return c.json(await dispatchFreefireRequest(region, '/GetPlayerGalleryInfoSetting', payload, 'CSGetPlayerGalleryInfoSettingRes'))
  } catch (e) {
    return c.json({ error: `Failed to fetch gallery show info: ${errMsg(e)}` }, 500)
  }
})

app.get('/wishlist/leaderboard', async (c) => {
  const region = regionParam(c)
  try {
    return c.json(await dispatchFreefireRequest(region, '/GetWishListLeaderboard', Buffer.alloc(0), 'CSGetWishListLeaderboardRes'))
  } catch (e) {
    return c.json({ error: `Failed to fetch wishlist leaderboard: ${errMsg(e)}` }, 500)
  }
})

app.on(['GET', 'POST'], '/occupation/set_new_season_show', async (c) => {
  let body = {}
  if ((c.req.header('content-type') ?? '').includes('application/json')) {
    body = await c.req.json().catch(() => ({}))
  }
  const gameMode = c.req.query('game_mode') ?? body.game_mode
  const matchMode = c.req.query('match_mode') ?? body.match_mode
  const region = regionParam(c)
  if (gameMode == null || matchMode == null) {
    return c.json({ error: "Please provide both 'game_mode' and 'match_mode'." }, 400)
  }
  try {
    if (!isInt(String(gameMode)) || !isInt(String(matchMode))) throw new Error('invalid game_mode or match_mode')
    const payload = buildPayload([[1, 'varint', String(gameMode).trim()], [2, 'varint', String(matchMode).trim()]])
    const data = await dispatchFreefireRequest(region, '/SetOccupationNewSeasonShow', payload, null)
    return c.json({ success: true, data })
  } catch (e) {
    return c.json({ error: `Failed to set occupation new season show: ${errMsg(e)}` }, 500)
  }
})

app.on(['GET', 'POST'], '/batch_get', async (c) => {
  const region = regionParam(c)
  let uids = []
  if (c.req.method === 'POST') {
    const body = await c.req.json().catch(() => ({}))
    uids = Array.isArray(body?.uids) ? body.uids.map(String) : []
  } else {
    uids = (c.req.query('uids') ?? '').split(',').map((u) => u.trim()).filter(Boolean)
  }
  if (uids.length === 0) return c.json({ error: 'Please provide a list of UIDs.' }, 400)
  try {
    const list = uids.slice(0, 50) // cap at 50 per batch
    if (!list.every(isInt)) throw new Error('all UIDs must be integers')
    const payload = buildPayload([[1, 'packed', list.map((u) => u.trim())], [2, 'varint', 7]])
    return c.json(await dispatchFreefireRequest(region, '/BatchGetAccountInfo', payload, 'CSBatchGetAccountInfoRes'))
  } catch (e) {
    return c.json({ error: `Batch lookup failed: ${errMsg(e)}` }, 500)
  }
})

app.get('/leaderboard', async (c) => {
  const region = regionParam(c)
  try {
    const mainType = parseInt(c.req.query('type') ?? '1', 10) // 1 = BR Ranked, 2 = CS Ranked
    const pageIndex = parseInt(c.req.query('page') ?? '0', 10)
    const pageSize = parseInt(c.req.query('size') ?? '50', 10)
    if ([mainType, pageIndex, pageSize].some(Number.isNaN)) throw new Error('type, page and size must be integers')
    const ReqType = lookupType('CSLeaderboardReq')
    const payload = ReqType.encode(
      ReqType.fromObject({
        main_type: mainType,
        sub_type: 0,
        page_index: pageIndex,
        page_size: pageSize,
        get_self: true,
        region,
        lock_region: region,
      }),
    ).finish()
    return c.json(await dispatchFreefireRequest(region, '/Leaderboard', payload, 'CSLeaderboardRes'))
  } catch (e) {
    return c.json({ error: `Failed to retrieve leaderboard: ${errMsg(e)}` }, 500)
  }
})

app.get('/check_ban', async (c) => {
  const uid = c.req.query('uid')
  const lang = c.req.query('lang') ?? 'en'
  if (!uid) return c.json({ error: 'Please provide UID.' }, 400)
  try {
    const url = new URL('https://ff.garena.com/api/antihack/check_banned')
    url.searchParams.set('lang', lang)
    url.searchParams.set('uid', uid)
    const resp = await fetch(url, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        Referer: 'https://ff.garena.com/en/support/',
        'X-Requested-With': 'B6FksShzIgjfrYImLpTsadjS86sddhFH',
        Accept: 'application/json, text/plain, */*',
      },
      signal: AbortSignal.timeout(10000),
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    return c.json(await resp.json())
  } catch (e) {
    return c.json({ error: `Anti-hack check error: ${errMsg(e)}` }, 500)
  }
})

app.on(['GET', 'POST'], '/refresh', async (c) => {
  try {
    await initializeTokens()
    return c.json({ message: 'Tokens refreshed for all regions.' })
  } catch (e) {
    return c.json({ error: errMsg(e) }, 500)
  }
})

app.notFound((c) => c.json({ error: 'Not found', hint: 'See / for the list of endpoints.' }, 404))

export default app
