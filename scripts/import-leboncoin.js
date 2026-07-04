/* ============================================================================
   Leboncoin importer — manual source, deliberately no scraping
   ----------------------------------------------------------------------------
   POLICY — why this script does not fetch leboncoin.fr pages:
   • leboncoin.fr/robots.txt opens with: "It's forbidden to use search robots
     or other automatic methods to access Leboncoin.fr. Access is only
     permitted with special permission from Leboncoin.fr."
   • The public seller page path (/profile/) is Disallow-ed even for the
     "friendly" crawlers they whitelist (Googlebot, bingbot, …).
   • Their CGU prohibit automated extraction/reuse of listings (French
     database right, Code de la propriété intellectuelle L342-1).
   So the compliant source is you, the seller: maintain your own listings in
   data/leboncoin-manual.json (you wrote those listings — copying your own
   title/price/photo into a file you own is not scraping). This script only
   validates + normalizes that file into data/leboncoin.json.

   Usage:
     npm run import:leboncoin            # normalize data/leboncoin-manual.json
     node scripts/import-leboncoin.js --check-policy
                                         # re-inspect robots.txt (informational)
   ========================================================================== */
import path from 'node:path';
import {
  DATA_DIR, ROOT, checkRobotsPolicy, normalizeItem, readManualFile, writeJson
} from './lib/normalize.js';

const SOURCE_FILE = path.join(DATA_DIR, 'leboncoin-manual.json');
const OUT_FILE = path.join(DATA_DIR, 'leboncoin.json');

async function main() {
  if (process.argv.includes('--check-policy')) {
    await checkRobotsPolicy('https://www.leboncoin.fr', ['profile', 'profil']);
    return;
  }

  const { items, missing } = readManualFile(SOURCE_FILE);
  if (missing) console.log(`No ${path.relative(ROOT, SOURCE_FILE)} — writing an empty listing set.`);

  const seen = new Set();
  const normalized = [];
  for (const raw of items) {
    const item = normalizeItem(raw, 'leboncoin');
    if (!item) continue;
    // Dedupe by listing URL / platform id within the source file.
    const key = item.source_url || item.source_platform_id || item.id;
    if (seen.has(key)) {
      console.warn(`  ! duplicate leboncoin entry skipped: ${key}`);
      continue;
    }
    seen.add(key);
    normalized.push(item);
  }

  writeJson(OUT_FILE, { source: 'leboncoin', count: normalized.length, items: normalized });
  console.log(`leboncoin: ${normalized.length} listing(s) → ${path.relative(ROOT, OUT_FILE)}`);
}

main().catch((e) => {
  console.error(`import-leboncoin failed: ${e.message}`);
  process.exitCode = 1;
});
