const STORAGE_KEY = 'demo_shop_cart_v1'

function safeParse (text, fallback) {
  try {
    const v = JSON.parse(text)
    return v == null ? fallback : v
  } catch (e) {
    return fallback
  }
}

function emitUpdated () {
  try {
    window.dispatchEvent(new Event('cart:updated'))
  } catch (e) {
    // ignore
  }
}

function normalizeItem (raw) {
  if (!raw) return null
  const id = Number(raw.id || raw.thingId)
  if (!id) return null
  const count = Math.max(1, Number(raw.count || 1) || 1)

  return {
    id,
    title: String(raw.title || ''),
    price: String(raw.price || ''),
    cover: String(raw.cover || ''),
    count,
    classification_title: raw.classification_title ? String(raw.classification_title) : undefined
  }
}

export function getItems () {
  const list = safeParse(localStorage.getItem(STORAGE_KEY) || '[]', [])
  if (!Array.isArray(list)) return []
  return list.map(normalizeItem).filter(Boolean)
}

export function setItems (items) {
  const normalized = (Array.isArray(items) ? items : []).map(normalizeItem).filter(Boolean)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized))
  emitUpdated()
  return normalized
}

export function clearCart () {
  localStorage.removeItem(STORAGE_KEY)
  emitUpdated()
}

export function getCount () {
  return getItems().reduce((sum, it) => sum + (Number(it.count) || 0), 0)
}

export function getTotalAmount () {
  return getItems().reduce((sum, it) => {
    const price = Number(it.price) || 0
    const count = Number(it.count) || 0
    return sum + price * count
  }, 0)
}

export function addItem (item, count = 1) {
  const next = getItems()
  const normalized = normalizeItem({ ...item, count })
  if (!normalized) return next

  const idx = next.findIndex(x => Number(x.id) === Number(normalized.id))
  if (idx >= 0) {
    next[idx].count = Math.min(99, (Number(next[idx].count) || 0) + (Number(normalized.count) || 1))
  } else {
    next.unshift(normalized)
  }
  return setItems(next)
}

export function removeItem (thingId) {
  const id = Number(thingId)
  const next = getItems().filter(x => Number(x.id) !== id)
  return setItems(next)
}

export function updateCount (thingId, count) {
  const id = Number(thingId)
  const next = getItems()
  const idx = next.findIndex(x => Number(x.id) === id)
  if (idx < 0) return next
  next[idx].count = Math.max(1, Math.min(99, Number(count) || 1))
  return setItems(next)
}
