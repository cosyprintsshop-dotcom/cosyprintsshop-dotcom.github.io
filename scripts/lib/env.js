/* Minimal .env loader — no dependency, keeps the site build-tool-free.
   Loads the given files in order if they exist, and NEVER overwrites a variable
   already present in the real environment, so CI / Cloudflare Pages dashboard
   values always win over a local file. Values may be single/double quoted.

   Default files: root `.env`, then `studio/.env` — the Sanity project id lives
   in studio/.env (gitignored, non-secret), so a local `npm run sync:catalog`
   picks it up without extra setup. */
import fs from 'node:fs';
import path from 'node:path';
import { ROOT } from './normalize.js';

export function loadEnv(files = ['.env', path.join('studio', '.env')]) {
  for (const rel of files) {
    const file = path.isAbsolute(rel) ? rel : path.join(ROOT, rel);
    if (!fs.existsSync(file)) continue;
    for (const raw of fs.readFileSync(file, 'utf8').split('\n')) {
      const line = raw.trim();
      if (!line || line.startsWith('#')) continue;
      const eq = line.indexOf('=');
      if (eq === -1) continue;
      const key = line.slice(0, eq).trim();
      let val = line.slice(eq + 1).trim();
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        val = val.slice(1, -1);
      }
      if (key && !(key in process.env)) process.env[key] = val;
    }
  }
}
