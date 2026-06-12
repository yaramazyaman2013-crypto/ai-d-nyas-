// JARVIS'in Minecraft bedeni — Mineflayer botu.
//
// Çalıştır:  node bot.js --host localhost --port <LAN_PORTU>
//
// Bir WebSocket SUNUCUSU (port 8765) açar. Python beyni (mc_bridge.py) buraya
// bağlanıp {"action": "...", "params": {...}} JSON'u gönderir; bot işi yapıp
// {"ok": true, "message": "..."} ile cevap verir.

const mineflayer = require('mineflayer')
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder')
const { WebSocketServer } = require('ws')

// ── Komut satırı argümanları ───────────────────────────────────────────────
function arg(name, def) {
  const i = process.argv.indexOf('--' + name)
  return i !== -1 ? process.argv[i + 1] : def
}
const HOST = arg('host', 'localhost')
const PORT = parseInt(arg('port', '25565'), 10)
const USERNAME = arg('username', 'Jarvis')
const WS_PORT = parseInt(arg('wsport', '8765'), 10)

// ── Botu oluştur ───────────────────────────────────────────────────────────
const bot = mineflayer.createBot({ host: HOST, port: PORT, username: USERNAME })
bot.loadPlugin(pathfinder)

let mcData = null
let defaultMove = null
let following = null // takip edilen oyuncu adı

bot.once('spawn', () => {
  mcData = require('minecraft-data')(bot.version)
  defaultMove = new Movements(bot, mcData)
  bot.pathfinder.setMovements(defaultMove)
  console.log(`[bot] Oyuna girdim: ${bot.username} @ ${HOST}:${PORT}`)
  bot.chat('Jarvis hazır.')
})

bot.on('error', (e) => console.log('[bot] hata:', e.message))
bot.on('kicked', (r) => console.log('[bot] atıldım:', r))
bot.on('end', () => console.log('[bot] bağlantı koptu.'))

// Takip modu: her fizik adımında oyuncuya yönel.
bot.on('physicsTick', () => {
  if (!following) return
  const target = bot.players[following]?.entity
  if (target) {
    bot.pathfinder.setGoal(new goals.GoalFollow(target, 2), true)
  }
})

// ── Beceriler ──────────────────────────────────────────────────────────────
function nearestPlayer() {
  // Bota en yakın gerçek oyuncuyu bul (botun kendisi hariç).
  let best = null, bestD = Infinity
  for (const name in bot.players) {
    const e = bot.players[name]?.entity
    if (!e || name === bot.username) continue
    const d = bot.entity.position.distanceTo(e.position)
    if (d < bestD) { bestD = d; best = bot.players[name] }
  }
  return best
}

const skills = {
  async come() {
    const p = nearestPlayer()
    if (!p?.entity) return 'Seni göremiyorum, yakında mısın?'
    following = null
    const { x, y, z } = p.entity.position
    await bot.pathfinder.goto(new goals.GoalNear(x, y, z, 1))
    return 'Yanına geldim.'
  },

  async follow() {
    const p = nearestPlayer()
    if (!p) return 'Takip edecek oyuncu bulamadım.'
    following = p.username
    return `${p.username} takip ediliyor.`
  },

  async stop() {
    following = null
    bot.pathfinder.setGoal(null)
    bot.clearControlStates()
    return 'Durdum.'
  },

  async chop_tree({ count = 1 } = {}) {
    const logIds = Object.keys(mcData.blocksByName)
      .filter((n) => n.endsWith('_log'))
      .map((n) => mcData.blocksByName[n].id)
    let chopped = 0
    for (let i = 0; i < count; i++) {
      const block = bot.findBlock({ matching: logIds, maxDistance: 32 })
      if (!block) break
      await bot.pathfinder.goto(new goals.GoalNear(
        block.position.x, block.position.y, block.position.z, 1))
      try { await bot.dig(block); chopped++ } catch { /* ulaşılamadı */ }
    }
    return chopped ? `${chopped} odun kestim.` : 'Yakında ağaç yok.'
  },

  async collect({ block, count = 1 } = {}) {
    const def = mcData.blocksByName[block]
    if (!def) return `'${block}' diye bir blok tanımıyorum.`
    let got = 0
    for (let i = 0; i < count; i++) {
      const found = bot.findBlock({ matching: def.id, maxDistance: 32 })
      if (!found) break
      await bot.pathfinder.goto(new goals.GoalNear(
        found.position.x, found.position.y, found.position.z, 1))
      try { await bot.dig(found); got++ } catch { /* geç */ }
    }
    return got ? `${got} ${block} topladım.` : `Yakında ${block} yok.`
  },

  async attack() {
    const mob = bot.nearestEntity(
      (e) => e.type === 'mob' || e.type === 'hostile')
    if (!mob) return 'Yakında düşman yok.'
    await bot.pathfinder.goto(new goals.GoalNear(
      mob.position.x, mob.position.y, mob.position.z, 2))
    bot.attack(mob)
    return 'Saldırdım.'
  },

  async status() {
    const p = bot.entity.position
    const inv = bot.inventory.items()
      .map((i) => `${i.count}x ${i.name}`).join(', ') || 'boş'
    return `Can ${Math.round(bot.health)}, açlık ${Math.round(bot.food)}, ` +
      `konum ${Math.round(p.x)},${Math.round(p.y)},${Math.round(p.z)}. ` +
      `Envanter: ${inv}.`
  },

  async say({ text = '' } = {}) {
    bot.chat(text)
    return 'Söyledim.'
  },
}

// ── WebSocket sunucusu (Python köprüsü buraya bağlanır) ─────────────────────
const wss = new WebSocketServer({ port: WS_PORT })
console.log(`[bridge] WebSocket dinlemede: ws://localhost:${WS_PORT}`)

wss.on('connection', (ws) => {
  ws.on('message', async (raw) => {
    let msg
    try { msg = JSON.parse(raw.toString()) } catch {
      return ws.send(JSON.stringify({ ok: false, message: 'Geçersiz JSON.' }))
    }
    const fn = skills[msg.action]
    if (!fn) {
      return ws.send(JSON.stringify({
        ok: false, message: `Bilinmeyen komut: ${msg.action}` }))
    }
    try {
      const message = await fn(msg.params || {})
      ws.send(JSON.stringify({ ok: true, message }))
    } catch (e) {
      ws.send(JSON.stringify({ ok: false, message: `Hata: ${e.message}` }))
    }
  })
})
