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

  async craft({ item, count = 1 } = {}) {
    // Crafting table bul veya envanterde craft et
    const recipe = await bot.recipesFor(mcData.itemsByName[item]?.id, null, 1, null)
    if (!recipe || recipe.length === 0) return `${item} için tarif bilmiyorum.`
    try {
      const table = bot.findBlock({ matching: mcData.blocksByName['crafting_table']?.id, maxDistance: 32 })
      if (table) {
        await bot.pathfinder.goto(new goals.GoalNear(table.position.x, table.position.y, table.position.z, 1))
        await bot.craft(recipe[0], count, table)
      } else {
        await bot.craft(recipe[0], count, null)
      }
      return `${count}x ${item} yaptım.`
    } catch (e) {
      return `${item} yapamadım: ${e.message}`
    }
  },

  async eat({ food = null } = {}) {
    // Yiyecek bul ve ye
    const foods = bot.inventory.items().filter(i => bot.registry.itemsByName[i.name]?.food)
    const target = food
      ? foods.find(i => i.name.includes(food))
      : foods.sort((a,b) => (bot.registry.itemsByName[b.name]?.food?.saturation||0) - (bot.registry.itemsByName[a.name]?.food?.saturation||0))[0]
    if (!target) return food ? `${food} envanterde yok.` : 'Yiyecek yok.'
    await bot.equip(target, 'hand')
    await bot.consume()
    return `${target.name} yedim. Açlık: ${Math.round(bot.food)}.`
  },

  async sleep() {
    const bed = bot.findBlock({
      matching: (b) => bot.isABed(b),
      maxDistance: 32
    })
    if (!bed) return 'Yakında yatak yok.'
    try {
      await bot.pathfinder.goto(new goals.GoalNear(bed.position.x, bed.position.y, bed.position.z, 1))
      await bot.sleep(bed)
      return 'Uyuyorum.'
    } catch (e) {
      return `Uyuyamadım: ${e.message}`
    }
  },

  async inventory() {
    const items = bot.inventory.items()
    if (!items.length) return 'Envanter boş.'
    const summary = {}
    for (const i of items) summary[i.name] = (summary[i.name] || 0) + i.count
    return 'Envanter: ' + Object.entries(summary).map(([n,c]) => `${c}x ${n}`).join(', ') + '.'
  },

  async drop({ item, count = 1 } = {}) {
    const found = bot.inventory.items().find(i => i.name.includes(item))
    if (!found) return `${item} envanterde yok.`
    await bot.toss(found.type, null, Math.min(count, found.count))
    return `${count}x ${item} düşürdüm.`
  },

  async equip({ item } = {}) {
    const found = bot.inventory.items().find(i => i.name.includes(item))
    if (!found) return `${item} envanterde yok.`
    await bot.equip(found, 'hand')
    return `${item} elimde.`
  },

  async place_block({ block, x, y, z } = {}) {
    const found = bot.inventory.items().find(i => i.name.includes(block))
    if (!found) return `${block} envanterde yok.`
    await bot.equip(found, 'hand')
    const refBlock = bot.blockAt(new (require('vec3'))(x, y - 1, z))
    if (!refBlock) return 'Hedef konum geçersiz.'
    await bot.placeBlock(refBlock, new (require('vec3'))(0, 1, 0))
    return `${block} yerleştirdim.`
  },

  async go_to({ x, y, z } = {}) {
    following = null
    await bot.pathfinder.goto(new goals.GoalNear(x, y, z, 1))
    return `${x}, ${y}, ${z} konumuna geldim.`
  },

  async mine({ block, count = 1 } = {}) {
    const def = mcData.blocksByName[block]
    if (!def) return `'${block}' bloğunu tanımıyorum.`
    let mined = 0
    for (let i = 0; i < count; i++) {
      const found = bot.findBlock({ matching: def.id, maxDistance: 32 })
      if (!found) break
      const tool = bot.pathfinder.bestHarvestTool(found)
      if (tool) await bot.equip(tool, 'hand')
      await bot.pathfinder.goto(new goals.GoalNear(found.position.x, found.position.y, found.position.z, 1))
      try { await bot.dig(found); mined++ } catch {}
    }
    return mined ? `${mined} ${block} kazıdım.` : `Yakında ${block} yok.`
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

bot.on('health', () => {
  if (bot.health < 8 && bot.food > 0) {
    // düşük can — yemek ye
    const food = bot.inventory.items().find(i => bot.registry.itemsByName[i.name]?.food)
    if (food) {
      bot.equip(food, 'hand').then(() => bot.consume()).catch(() => {})
    }
  }
})
