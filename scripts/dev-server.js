/* Tiny zero-dependency static server for local preview: `npm run dev`.
   GitHub Pages serves the same files in production — this is dev-only. */
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { ROOT } from './lib/normalize.js';

const PORT = Number(process.env.PORT) || 8080;
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
  '.woff2': 'font/woff2'
};

http.createServer((req, res) => {
  const urlPath = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  let file = path.join(ROOT, path.normalize(urlPath).replace(/^([/\\])+/, ''));
  if (!file.startsWith(ROOT)) { res.writeHead(403).end(); return; }
  if (urlPath === '/' || !path.extname(file)) file = path.join(ROOT, urlPath === '/' ? 'index.html' : urlPath + '.html');
  if (!fs.existsSync(file)) {
    res.writeHead(404, { 'Content-Type': MIME['.html'] });
    res.end(fs.existsSync(path.join(ROOT, '404.html')) ? fs.readFileSync(path.join(ROOT, '404.html')) : 'Not found');
    return;
  }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream' });
  res.end(fs.readFileSync(file));
}).listen(PORT, () => console.log(`cosyprints dev server → http://localhost:${PORT}`));
