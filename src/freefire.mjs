// Core Free Fire client: AES payload encryption, JWT handling and
// protobuf request/response decoding. Port of core/*.py.
import { createCipheriv } from 'node:crypto'
import protobuf from 'protobufjs'
import Long from 'long'

import protoJson from './proto.json' with { type: 'json' }
import accounts from '../accounts.json' with { type: 'json' }

export const SUPPORTED_REGIONS = new Set([
  'SG', 'IND', 'BR', 'US', 'SAC', 'NA', 'RU', 'ID', 'TW', 'VN', 'TH', 'ME', 'PK', 'BD',
])

const RELEASE_VERSION = 'OB55'
const USER_AGENT = 'ART/2.2.0 (Linux; U; Android 14; SAMSUNG_S25 Build/UP1A.240905.001)'
const JWT_API_URL = 'https://wzjwt.vercel.app/token'

const MAIN_KEY = Buffer.from('WWcmdGMlREV1aDYlWmNeOA==', 'base64')
const MAIN_IV = Buffer.from('Nm95WkRyMjJFM3ljaGpNJQ==', 'base64')

// ---------------------------------------------------------------------------
// Protobuf schema
// ---------------------------------------------------------------------------

protobuf.util.Long = Long
protobuf.configure()

const root = protobuf.Root.fromJSON(protoJson)
root.resolveAll()

export function lookupType(name) {
  return root.lookupType(`freefire.${name}`)
}

// ---------------------------------------------------------------------------
// Encoding helpers
// ---------------------------------------------------------------------------

export function aesCbcEncrypt(plaintext) {
  // Node's default PKCS#7 padding matches the original implementation.
  const cipher = createCipheriv('aes-128-cbc', MAIN_KEY, MAIN_IV)
  return Buffer.concat([cipher.update(plaintext), cipher.final()])
}

/** Encode a non-negative integer (number, string or bigint) as a protobuf varint. */
export function encodeVarint(value) {
  let v = BigInt(value)
  if (v < 0n) v = BigInt.asUintN(64, v)
  const out = []
  do {
    let byte = Number(v & 0x7fn)
    v >>= 7n
    if (v > 0n) byte |= 0x80
    out.push(byte)
  } while (v > 0n)
  return out
}

/** Build a payload from a list of [fieldNumber, kind, value] entries. */
export function buildPayload(fields) {
  const bytes = []
  for (const [fieldNo, kind, value] of fields) {
    if (kind === 'varint') {
      bytes.push(...encodeVarint((fieldNo << 3) | 0), ...encodeVarint(value))
    } else if (kind === 'string') {
      const buf = Buffer.from(String(value), 'utf8')
      bytes.push(...encodeVarint((fieldNo << 3) | 2), ...encodeVarint(buf.length), ...buf)
    } else if (kind === 'packed') {
      const inner = value.flatMap((v) => encodeVarint(v))
      bytes.push(...encodeVarint((fieldNo << 3) | 2), ...encodeVarint(inner.length), ...inner)
    }
  }
  return Buffer.from(bytes)
}

// ---------------------------------------------------------------------------
// Protobuf -> JSON, matching Python's json_format.MessageToJson with
// preserving_proto_field_name and always_print_fields_with_no_presence.
// ---------------------------------------------------------------------------

const LONG_TYPES = new Set(['int64', 'uint64', 'sint64', 'fixed64', 'sfixed64'])

function shortestFloat32(v) {
  if (!Number.isFinite(v)) return v
  for (let p = 1; p <= 9; p++) {
    const candidate = Number(v.toPrecision(p))
    if (Math.fround(candidate) === v) return candidate
  }
  return v
}

function scalarToJson(field, value) {
  const resolved = field.resolvedType
  if (resolved instanceof protobuf.Enum) {
    const name = resolved.valuesById[value]
    return name === undefined ? value : name
  }
  if (resolved instanceof protobuf.Type) {
    return messageToJson(value, resolved)
  }
  if (LONG_TYPES.has(field.type)) {
    if (Long.isLong(value)) return value.toString()
    return String(value ?? 0)
  }
  if (field.type === 'bytes') {
    return Buffer.from(value ?? []).toString('base64')
  }
  if (field.type === 'float' || field.type === 'double') {
    let num = field.type === 'float' ? shortestFloat32(value) : value
    if (Number.isNaN(num)) return 'NaN'
    if (num === Infinity) return 'Infinity'
    if (num === -Infinity) return '-Infinity'
    return num
  }
  return value
}

export function messageToJson(message, type) {
  const out = {}
  for (const field of type.fieldsArray) {
    const value = message[field.name]
    if (field.map) {
      const obj = {}
      for (const [k, v] of Object.entries(value ?? {})) obj[k] = scalarToJson(field, v)
      out[field.name] = obj
    } else if (field.repeated) {
      out[field.name] = (value ?? []).map((v) => scalarToJson(field, v))
    } else if (field.resolvedType instanceof protobuf.Type) {
      // Sub-messages have presence: only emit them when set.
      if (value != null) out[field.name] = messageToJson(value, field.resolvedType)
    } else {
      out[field.name] = scalarToJson(field, value)
    }
  }
  return out
}

// ---------------------------------------------------------------------------
// Account credentials and JWT cache
// ---------------------------------------------------------------------------

const ACCOUNTS_BY_REGION = new Map()
try {
  for (const entry of accounts) {
    const region = String(entry.region ?? '').toUpperCase()
    if (region && SUPPORTED_REGIONS.has(region)) {
      ACCOUNTS_BY_REGION.set(region, { uid: String(entry.uid), password: String(entry.password) })
    }
  }
} catch (err) {
  console.error('Error loading accounts.json:', err)
}

const FALLBACK_ACCOUNT = {
  uid: '3937206629',
  password: 'E4D17A3799816184A9BA20C68D8DE55C69180F8C793CA1C6B164C6D14848D8DF',
}

function getAccountCredentials(region) {
  return ACCOUNTS_BY_REGION.get(region.toUpperCase()) ?? FALLBACK_ACCOUNT
}

// In-memory token cache (tokens are short-lived and simply re-fetched after a cold start).
const cachedTokens = new Map()
const pendingTokens = new Map()

async function fetchWithTimeout(url, options = {}, timeoutMs = 15000) {
  return fetch(url, { ...options, signal: AbortSignal.timeout(timeoutMs) })
}

export async function createJwt(region) {
  const { uid, password } = getAccountCredentials(region)
  const resp = await fetchWithTimeout(JWT_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ uid, password }),
  })
  if (!resp.ok) throw new Error(`Token API responded with HTTP ${resp.status}`)
  const data = await resp.json()
  if (data.status !== 'success') {
    throw new Error(`External API error: ${data.message ?? 'Unknown error'}`)
  }
  const inner = data.data ?? {}
  const jwt = inner.token
  const serverUrl = inner.server_url
  const ttl = Number(inner.ttl ?? 25200)
  if (!jwt || !serverUrl) throw new Error('Missing token or server_url in API response data')

  const info = {
    token: `Bearer ${jwt}`,
    region: inner.lock_region ?? region,
    serverUrl,
    expiresAt: Date.now() + ttl * 1000,
  }
  cachedTokens.set(region, info)
  return info
}

export async function getTokenInfo(region) {
  const info = cachedTokens.get(region)
  if (info && Date.now() < info.expiresAt) return info

  // De-duplicate concurrent token requests for the same region.
  if (!pendingTokens.has(region)) {
    pendingTokens.set(region, createJwt(region).finally(() => pendingTokens.delete(region)))
  }
  return pendingTokens.get(region)
}

export async function initializeTokens() {
  return Promise.allSettled([...SUPPORTED_REGIONS].map((r) => createJwt(r)))
}

// ---------------------------------------------------------------------------
// Game server requests
// ---------------------------------------------------------------------------

/**
 * Send an encrypted protobuf request to the game server for a region and
 * decode the response. When `responseType` is null the raw response body is
 * returned as base64.
 */
export async function dispatchFreefireRequest(region, endpoint, rawPayload, responseType) {
  region = region.toUpperCase()
  if (!SUPPORTED_REGIONS.has(region)) throw new Error(`Unsupported region: ${region}`)

  const body = aesCbcEncrypt(rawPayload)
  const { token, serverUrl } = await getTokenInfo(region)

  const resp = await fetchWithTimeout(
    serverUrl + endpoint,
    {
      method: 'POST',
      headers: {
        'User-Agent': USER_AGENT,
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/octet-stream',
        Authorization: token,
        'X-Unity-Version': '2018.4.11f1',
        'X-GA': 'v1 1',
        ReleaseVersion: RELEASE_VERSION,
      },
      body,
    },
    12000,
  )
  if (!resp.ok) {
    throw new Error(`Server error '${resp.status} ${resp.statusText}' for url '${serverUrl + endpoint}'`)
  }
  const content = new Uint8Array(await resp.arrayBuffer())

  if (!responseType) {
    return { raw: Buffer.from(content).toString('base64') }
  }
  const type = typeof responseType === 'string' ? lookupType(responseType) : responseType
  const message = type.decode(content)
  return messageToJson(message, type)
}
