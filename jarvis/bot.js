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

  // ── Madencilik görevi ────────────────────────────────────────────────────
  async mine_mission({ ore = 'coal_ore', amount = 32 } = {}) {
    // Kömür, demir, altın, elmas vb. için akıllı madencilik görevi.
    // Hem normal hem de deep variant'ı arar, uygun alet kullanır, döner.
    const aliases = {
      coal: ['coal_ore', 'deepslate_coal_ore'],
      iron: ['iron_ore', 'deepslate_iron_ore'],
      gold: ['gold_ore', 'deepslate_gold_ore'],
      diamond: ['diamond_ore', 'deepslate_diamond_ore'],
      lapis: ['lapis_ore', 'deepslate_lapis_ore'],
      redstone: ['redstone_ore', 'deepslate_redstone_ore'],
      emerald: ['emerald_ore', 'deepslate_deepslate_emerald_ore'],
      copper: ['copper_ore', 'deepslate_copper_ore'],
    }
    const targets = aliases[ore] || [ore, 'deepslate_' + ore]
    const oreIds = targets
      .map(n => mcData.blocksByName[n]?.id)
      .filter(Boolean)

    if (!oreIds.length) return `'${ore}' madeni tanımıyorum.`

    const startPos = bot.entity.position.clone()
    let mined = 0
    let attempts = 0
    const maxAttempts = amount * 3

    while (mined < amount && attempts < maxAttempts) {
      attempts++
      const block = bot.findBlock({ matching: oreIds, maxDistance: 64 })
      if (!block) break

      // Uygun kazma seç
      const pickaxes = ['netherite_pickaxe','diamond_pickaxe','iron_pickaxe','stone_pickaxe','wooden_pickaxe']
      for (const p of pickaxes) {
        const tool = bot.inventory.items().find(i => i.name === p)
        if (tool) { await bot.equip(tool, 'hand'); break }
      }

      try {
        await bot.pathfinder.goto(new goals.GoalNear(
          block.position.x, block.position.y, block.position.z, 1))
        await bot.dig(block)
        mined++
        // Sürüklenen eşyaları topla
        await new Promise(r => setTimeout(r, 400))
      } catch { /* blok kaybolmuş olabilir */ }

      // Envanter doldu mu?
      if (bot.inventory.emptySlotCount() < 2) break
    }

    // Oyuncuya geri dön
    const player = nearestPlayer()
    if (player?.entity) {
      const { x, y, z } = player.entity.position
      await bot.pathfinder.goto(new goals.GoalNear(x, y, z, 3))
    }

    const oreName = ore.charAt(0).toUpperCase() + ore.slice(1)
    return mined
      ? `${mined} ${oreName} madeni kazıp geri döndüm.`
      : `${oreName} madeni bulamadım (64 blok içinde yok veya alet eksik).`
  },

  // ── İnşaat sistemi ───────────────────────────────────────────────────────
  async build({ yapi = 'kulübe', malzeme = null } = {}) {
    const pos = bot.entity.position.floored()
    // Zemin seviyesine in
    const bx = pos.x, by = pos.y, bz = pos.z + 3

    // Kullanılabilir blok bul
    const matPriority = malzeme
      ? [malzeme]
      : ['oak_planks','spruce_planks','birch_planks','cobblestone','stone','dirt','sand']

    function findMat(names) {
      for (const n of names) {
        const item = bot.inventory.items().find(i => i.name === n)
        if (item && item.count > 0) return item
      }
      return null
    }

    const blueprints = {
      // Basit kulübe: 5x5 taban, 3 kat duvar, çatı
      'kulübe': () => {
        const blocks = []
        for (let y = 0; y < 4; y++) {
          for (let x = -2; x <= 2; x++) {
            for (let z = 0; z <= 4; z++) {
              const isWall = y === 0 || y === 3 || x === -2 || x === 2 || z === 0 || z === 4
              if (isWall) blocks.push([bx+x, by+y, bz+z])
            }
          }
        }
        // Çatı
        for (let x = -2; x <= 2; x++)
          for (let z = 0; z <= 4; z++)
            blocks.push([bx+x, by+4, bz+z])
        return blocks
      },
      // Kule: 3x3 taban, 15 kat
      'kule': () => {
        const blocks = []
        for (let y = 0; y < 15; y++) {
          for (let x = -1; x <= 1; x++) {
            for (let z = 0; z <= 2; z++) {
              if (x === -1 || x === 1 || z === 0 || z === 2)
                blocks.push([bx+x, by+y, bz+z])
            }
          }
        }
        // Tepesi
        for (let x = -1; x <= 1; x++)
          for (let z = 0; z <= 2; z++)
            blocks.push([bx+x, by+15, bz+z])
        return blocks
      },
      // Gökdelen: 7x7 taban, 30 kat, her 5 katta bir zemin (tavan/taban)
      'gökdelen': () => {
        const blocks = []
        const W = 3 // yarı genişlik
        for (let y = 0; y < 30; y++) {
          for (let x = -W; x <= W; x++) {
            for (let z = 0; z <= W*2; z++) {
              const isWall = x === -W || x === W || z === 0 || z === W*2
              const isFloor = y % 5 === 0
              if (isWall || isFloor) blocks.push([bx+x, by+y, bz+z])
            }
          }
        }
        // Çatı
        for (let x = -W; x <= W; x++)
          for (let z = 0; z <= W*2; z++)
            blocks.push([bx+x, by+30, bz+z])
        return blocks
      },
      // Köprü: 3 geniş, 20 blok uzun
      'köprü': () => {
        const blocks = []
        for (let z = 0; z < 20; z++)
          for (let x = -1; x <= 1; x++)
            blocks.push([bx+x, by, bz+z])
        return blocks
      },
      // Duvar: 1 kalın, 10 uzun, 5 yüksek
      'duvar': () => {
        const blocks = []
        for (let z = 0; z < 10; z++)
          for (let y = 0; y < 5; y++)
            blocks.push([bx, by+y, bz+z])
        return blocks
      },
    }

    const key = Object.keys(blueprints).find(k =>
      yapi.toLowerCase().includes(k) || k.includes(yapi.toLowerCase()))
    if (!key) {
      return `'${yapi}' yapısını bilmiyorum. Bildiğim yapılar: ${Object.keys(blueprints).join(', ')}.`
    }

    const blockList = blueprints[key]()
    const mat = findMat(matPriority)
    if (!mat) {
      const needed = Math.min(blockList.length, 64)
      return `İnşaat için malzeme yok. En az ${needed} blok gerekiyor (ahşap, taş, toprak vb.).`
    }

    let placed = 0
    let currentMat = mat

    for (const [wx, wy, wz] of blockList) {
      currentMat = findMat(matPriority)
      if (!currentMat) break

      try {
        await bot.equip(currentMat, 'hand')
        // Botun yerleştirebileceği konuma git
        await bot.pathfinder.goto(new goals.GoalNear(wx, wy, wz, 2))
        const ref = bot.blockAt(new (require('vec3'))(wx, wy - 1, wz))
        if (ref && ref.name !== 'air') {
          await bot.placeBlock(ref, new (require('vec3'))(0, 1, 0))
          placed++
        }
      } catch { /* blok zaten var veya ulaşılamıyor */ }
    }

    return placed > 0
      ? `${key} inşa ettim — ${placed} blok yerleştirdim.`
      : `${key} inşa edemedim. Malzeme veya yer sorunu olabilir.`
  },

  // ── Özel/serbest inşaat (LLM kendi tasarlar) ──────────────────────────────
  // blocks: bota göre relatif koordinatlardaki blok listesi
  //   [{ dx, dy, dz, block }]  — yapay zekâ herhangi bir yapıyı tasarlayıp gönderir.
  async build_custom({ blocks = [] } = {}) {
    if (!Array.isArray(blocks) || blocks.length === 0) {
      return 'İnşa edilecek blok listesi boş.'
    }
    const Vec3 = require('vec3')
    // Botun 2 blok önündeki konumu taban al
    const base = bot.entity.position.floored().offset(0, 0, 2)

    // Alttan üste sırala — her blok altındaki bloğa dayanarak yerleşsin
    const sorted = blocks.slice().sort((a, b) => (a.dy || 0) - (b.dy || 0))

    let placed = 0, eksikMalzeme = 0, ulasamadi = 0
    const usedMaterials = new Set()

    for (const b of sorted) {
      const blockName = (b.block || '').toLowerCase()
      const item = bot.inventory.items().find(
        i => i.name === blockName || i.name.includes(blockName))
      if (!item) { eksikMalzeme++; usedMaterials.add(blockName); continue }

      const target = base.offset(b.dx || 0, b.dy || 0, b.dz || 0)
      try {
        await bot.equip(item, 'hand')
        await bot.pathfinder.goto(new goals.GoalNear(target.x, target.y, target.z, 3))
        // Altındaki, yanındaki veya üstündeki dolu bir komşuya dayan
        const neighbors = [
          [target.offset(0, -1, 0), new Vec3(0, 1, 0)],
          [target.offset(0, 1, 0), new Vec3(0, -1, 0)],
          [target.offset(1, 0, 0), new Vec3(-1, 0, 0)],
          [target.offset(-1, 0, 0), new Vec3(1, 0, 0)],
          [target.offset(0, 0, 1), new Vec3(0, 0, -1)],
          [target.offset(0, 0, -1), new Vec3(0, 0, 1)],
        ]
        let done = false
        for (const [refPos, face] of neighbors) {
          const ref = bot.blockAt(refPos)
          if (ref && ref.name !== 'air' && ref.boundingBox === 'block') {
            try { await bot.placeBlock(ref, face); placed++; done = true; break } catch {}
          }
        }
        if (!done) ulasamadi++
      } catch { ulasamadi++ }
    }

    let msg = `Yapıyı kurdum — ${placed} blok yerleştirdim.`
    if (eksikMalzeme > 0) {
      msg += ` ${eksikMalzeme} blok için malzeme yetmedi (${[...usedMaterials].join(', ')}).`
    }
    if (ulasamadi > 0) msg += ` ${ulasamadi} blok ulaşılamadı/havada kaldı.`
    return msg
  },

  // ── Hayatta kalma görevi ─────────────────────────────────────────────────
  async survive({ sure = 60 } = {}) {
    // Belirtilen süre boyunca (saniye) hayatta kalır:
    // ağaç kes → odun craft → yemek ara → düşman varsa savaş
    const end = Date.now() + sure * 1000
    const log = []

    while (Date.now() < end) {
      // Açlık kontrolü
      if (bot.food < 14) {
        const food = bot.inventory.items().find(i => bot.registry.itemsByName[i.name]?.food)
        if (food) {
          await bot.equip(food, 'hand')
          try { await bot.consume(); log.push('yedim') } catch {}
        }
      }

      // Düşman varsa savaş
      const mob = bot.nearestEntity(e => e.type === 'mob' &&
        bot.entity.position.distanceTo(e.position) < 8)
      if (mob) {
        await bot.pathfinder.goto(new goals.GoalNear(
          mob.position.x, mob.position.y, mob.position.z, 2))
        bot.attack(mob)
        log.push('savaştım')
        await new Promise(r => setTimeout(r, 1000))
        continue
      }

      // Odun topla
      const logIds = Object.keys(mcData.blocksByName)
        .filter(n => n.endsWith('_log'))
        .map(n => mcData.blocksByName[n].id)
      const tree = bot.findBlock({ matching: logIds, maxDistance: 16 })
      if (tree) {
        await bot.pathfinder.goto(new goals.GoalNear(
          tree.position.x, tree.position.y, tree.position.z, 1))
        try { await bot.dig(tree); log.push('odun') } catch {}
      }

      await new Promise(r => setTimeout(r, 500))
    }

    const summary = {}
    for (const a of log) summary[a] = (summary[a] || 0) + 1
    return 'Hayatta kalma görevi bitti: ' +
      Object.entries(summary).map(([k,v]) => `${k}(${v})`).join(', ') + '.'
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
