/* ============================================================================
   Cosy Prints — shared catalogue normalization
   ----------------------------------------------------------------------------
   Used by scripts/import-leboncoin.js, scripts/import-vinted.js and
   scripts/sync-catalog.js. Turns loosely-typed manual entries into the
   canonical item shape consumed by assets/products.js / boutique.html.

   Canonical item (key order is stable so JSON diffs stay readable):
     id, source, source_url, source_platform_id,
     title_fr, title_en, desc_fr, desc_en,
     price, currency, img, images,
     category, badge, status,
     platform, location, material,
     created_at, updated_at
   ========================================================================== */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const DATA_DIR = path.join(ROOT, 'data');

/* Must match CATEGORIES in boutique.html — keep the two lists in sync. */
export const CATEGORIES = ['homie-vibe', 'cable-management', 'lampes', 'bureau', 'gadgets'];
export const DEFAULT_CATEGORY = 'homie-vibe';

/* First matching group wins, so the more specific universes come first and
   'homie-vibe' acts as the deco catch-all. Keywords are accent-stripped
   lowercase because fold() is applied to the searched text. */
const CATEGORY_KEYWORDS = [
  ['cable-management', ['cable', 'chargeur', 'magsafe', 'usb', 'dock de charge']],
  ['lampes', ['lampe', 'lumiere', 'luminaire', 'veilleuse', 'applique', 'abat-jour', 'lampadaire', 'photophore', 'led']],
  ['bureau', ['bureau', 'rangement', 'organiseur', 'organisateur', 'support telephone', 'support casque', 'porte-stylo', 'stylo', 'crayon', 'clavier', 'laptop', 'macbook', 'tablette', 'ipad']],
  ['gadgets', ['gadget', 'ouvre-', 'decapsuleur', 'porte-cles', 'porte-cle', 'fidget', 'outil']],
  ['homie-vibe', ['vase', 'pot ', 'plante', 'deco', 'sculpture', 'cadre', 'etagere', 'bougie', 'dessous de verre', 'plateau']]
];

/* Badge slugs — rendered bilingually by boutique.html (BADGE_LABELS). */
const BADGE_RULES = [
  ['made-to-order', /sur commande|a la demande|made to order/],
  ['limited', /serie limitee|edition limitee|piece unique|limited/],
  ['eco-pla', /\bpla\b/]
];

/* Lowercase + strip accents, so keyword matching is diacritic-insensitive. */
export const fold = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');

export const slugify = (s) => fold(s).replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60);

export function inferCategory(text) {
  const t = fold(text);
  for (const [slug, words] of CATEGORY_KEYWORDS) {
    if (words.some((w) => t.includes(w))) return slug;
  }
  return DEFAULT_CATEGORY;
}

export function inferBadge(text) {
  const t = fold(text);
  for (const [slug, re] of BADGE_RULES) {
    if (re.test(t)) return slug;
  }
  return null;
}

/* "24,90 €", "24.90", 24.9 → 24.9 (EUR number). Returns null when unpriced. */
export function normalizePrice(value) {
  if (value == null || value === '') return null;
  if (typeof value === 'number') return Number.isFinite(value) && value >= 0 ? value : null;
  const cleaned = String(value).replace(/[€\s  ]/g, '').replace(',', '.');
  const n = Number.parseFloat(cleaned);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

/* Listing ids embedded in public URLs:
   leboncoin: …/ad/<category>/2894735  → 2894735
   vinted:    …/items/6152034921-vase  → 6152034921 */
export function platformIdFromUrl(url) {
  if (!url) return null;
  const m = String(url).match(/\/(?:items|ad)\/(?:[a-z0-9_-]+\/)?(\d{4,})/i) || String(url).match(/\/(\d{6,})(?:\.htm)?(?:[?#]|$)/);
  return m ? m[1] : null;
}

const cleanText = (s) => (s == null ? '' : String(s).replace(/\s+/g, ' ').trim());

/**
 * Normalize one manual entry into the canonical shape.
 * Returns null (and calls warn) when the entry is unusable (no title).
 */
export function normalizeItem(raw, source, warn = console.warn) {
  const title_fr = cleanText(raw.title_fr || raw.title);
  if (!title_fr) {
    warn(`  ! skipped ${source} entry without title_fr/title: ${JSON.stringify(raw).slice(0, 80)}…`);
    return null;
  }

  const source_url = cleanText(raw.source_url || raw.url) || null;
  const source_platform_id = cleanText(raw.source_platform_id) || platformIdFromUrl(source_url);
  const id = cleanText(raw.id) || `${source}-${source_platform_id || slugify(title_fr)}`;

  const desc_fr = cleanText(raw.desc_fr || raw.desc);
  const images = Array.isArray(raw.images) ? raw.images.map(cleanText).filter(Boolean) : [];
  const img = cleanText(raw.img) || images[0] || null;

  const currency = cleanText(raw.currency).toUpperCase() || 'EUR';
  if (currency !== 'EUR') warn(`  ! ${id}: currency ${currency} — the site renders prices as EUR`);

  let category = cleanText(raw.category);
  if (category && !CATEGORIES.includes(category)) {
    warn(`  ! ${id}: unknown category "${category}" (valid: ${CATEGORIES.join(', ')}) — inferring instead`);
    category = '';
  }

  const badgeBasis = `${title_fr} ${desc_fr} ${cleanText(raw.material)}`;
  return {
    id,
    source,
    source_url,
    source_platform_id: source_platform_id || null,
    title_fr,
    title_en: cleanText(raw.title_en) || null,
    desc_fr: desc_fr || null,
    desc_en: cleanText(raw.desc_en) || null,
    price: normalizePrice(raw.price),
    currency,
    img,
    images,
    category: category || inferCategory(badgeBasis),
    // An explicit "badge" key (even null) disables the heuristics.
    badge: 'badge' in raw ? (cleanText(raw.badge) || null) : inferBadge(badgeBasis),
    status: cleanText(raw.status) || 'active',
    platform: cleanText(raw.platform) || source,
    location: cleanText(raw.location) || null,
    material: cleanText(raw.material) || null,
    created_at: cleanText(raw.created_at) || null,
    updated_at: cleanText(raw.updated_at) || null
  };
}

/* ------------------------- manual source files ------------------------- */

/**
 * Read a hand-maintained source file ({ items: [...] }). A missing file is a
 * normal state (empty catalogue); malformed JSON is a hard error so a typo
 * never silently empties the shop.
 */
export function readManualFile(file) {
  if (!fs.existsSync(file)) return { items: [], missing: true };
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (e) {
    throw new Error(`${path.relative(ROOT, file)} is not valid JSON: ${e.message}`);
  }
  const items = Array.isArray(parsed) ? parsed : parsed.items;
  if (!Array.isArray(items)) throw new Error(`${path.relative(ROOT, file)}: expected { "items": [...] }`);
  return { items, missing: false };
}

export function readJsonIfExists(file) {
  if (!fs.existsSync(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return null;
  }
}

export function writeJson(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n', 'utf8');
}

/* Content fingerprint that ignores timestamps, so sync-catalog.js only
   refreshes updated_at when a listing actually changed. */
export function fingerprint(item) {
  const { created_at, updated_at, also_on, ...rest } = item;
  return JSON.stringify(rest);
}

/* --------------------------- policy check (opt-in) ---------------------- */

/**
 * `--check-policy` helper: fetches the platform's robots.txt (a file meant
 * for machines) and reports the lines relevant to seller/profile pages.
 * Purely informational — the importers never fetch listing pages, because
 * both platforms' terms prohibit automated extraction (see README).
 */
export async function checkRobotsPolicy(origin, needles) {
  const res = await fetch(`${origin}/robots.txt`, {
    headers: { 'User-Agent': 'CosyPrintsSiteSync/1.0 (site owner; cosyprints.shop@gmail.com)' }
  });
  if (!res.ok) {
    console.log(`${origin}/robots.txt → HTTP ${res.status}`);
    return;
  }
  const lines = (await res.text()).split('\n');
  console.log(`${origin}/robots.txt — leading comments and lines matching [${needles.join(', ')}]:`);
  for (const line of lines.slice(0, 5)) {
    if (line.trim().startsWith('#')) console.log(`  ${line.trim()}`);
  }
  for (const line of lines) {
    const l = line.toLowerCase();
    if (needles.some((n) => l.includes(n)) && /allow|disallow/i.test(l)) console.log(`  ${line.trim()}`);
  }
  console.log('Reminder: robots.txt is only one signal — the platform terms of use still apply.');
}
