/* ============================================================================
   Vinted importer — manual source, deliberately no scraping
   ----------------------------------------------------------------------------
   POLICY — why this script does not fetch vinted.fr pages:
   Vinted's Terms & Conditions prohibit crawling / screen-scraping of the
   platform, and there is no public export or public API for regular member
   catalogues. Of the compliant options considered (manual JSON, URL-list
   enrichment, CSV conversion), the manual JSON source file is the safest:
   URL "enrichment" would still mean automated page fetches (scraping), and
   a CSV adds a conversion step with no data Vinted actually exports. As the
   seller you already own every field — title, price, photo, URL — so
   maintaining data/vinted-manual.json is both compliant and low-friction.
   This script only validates + normalizes that file into data/vinted.json.

   Usage:
     npm run import:vinted               # normalize data/vinted-manual.json
     node scripts/import-vinted.js --check-policy
                                         # re-inspect robots.txt (informational)
   ========================================================================== */
import path from 'node:path';
import {
  DATA_DIR, ROOT, checkRobotsPolicy, normalizeItem, readManualFile, writeJson
} from './lib/normalize.js';

const SOURCE_FILE = path.join(DATA_DIR, 'vinted-manual.json');
const OUT_FILE = path.join(DATA_DIR, 'vinted.json');

async function main() {
  if (process.argv.includes('--check-policy')) {
    await checkRobotsPolicy('https://www.vinted.fr', ['member', 'items']);
    return;
  }

  const { items, missing } = readManualFile(SOURCE_FILE);
  if (missing) console.log(`No ${path.relative(ROOT, SOURCE_FILE)} — writing an empty listing set.`);

  const seen = new Set();
  const normalized = [];
  for (const raw of items) {
    const item = normalizeItem(raw, 'vinted');
    if (!item) continue;
    const key = item.source_url || item.source_platform_id || item.id;
    if (seen.has(key)) {
      console.warn(`  ! duplicate vinted entry skipped: ${key}`);
      continue;
    }
    seen.add(key);
    normalized.push(item);
  }

  writeJson(OUT_FILE, { source: 'vinted', count: normalized.length, items: normalized });
  console.log(`vinted: ${normalized.length} listing(s) → ${path.relative(ROOT, OUT_FILE)}`);
}

main().catch((e) => {
  console.error(`import-vinted failed: ${e.message}`);
  process.exitCode = 1;
});
