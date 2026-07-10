/* ============================================================================
   Sanity → static site bridge  (Phase 2)
   ----------------------------------------------------------------------------
   Fetches PUBLISHED content from Sanity and writes:
     data/sanity.json   → products in the manual-source shape, so sync-catalog.js
                          normalizes/dedupes/timestamps them like every other source.
     data/content.json  → homepage, impact, FAQ, site settings (for page rendering).

   Runs at build time (Cloudflare Pages) and locally. Requires SANITY_PROJECT_ID.
   When it is unset (e.g. before the Sanity project exists), this exits 0 and
   writes nothing, so the site still builds from the existing manual sources.
   ========================================================================== */
import path from 'node:path';
import {DATA_DIR, writeJson} from './lib/normalize.js';

const projectId = process.env.SANITY_PROJECT_ID;
const dataset = process.env.SANITY_DATASET || 'production';

if (!projectId) {
  console.log('fetch-sanity: SANITY_PROJECT_ID not set — skipping (no Sanity source yet).');
  process.exit(0);
}

// Imported dynamically so the build works even before `npm install` adds the dep.
const {createClient} = await import('@sanity/client');
const client = createClient({projectId, dataset, apiVersion: '2024-01-01', useCdn: true});

/* Exclude drafts: a content edit stays invisible on the site until Publish. */
const NOT_DRAFT = '!(_id in path("drafts.**"))';

/* Sanity image CDN transform: auto WebP/AVIF + sensible width, no repo bloat. */
const sized = (url, w = 1000) => (url ? `${url}?w=${w}&auto=format&fit=max` : null);

/* Portable-text blocks → plain text (for desc/FAQ answers consumed as text). */
const blocksToText = (blocks = []) =>
  blocks
    .filter((b) => b && b._type === 'block')
    .map((b) => (b.children || []).map((c) => c.text).join(''))
    .join('\n\n')
    .trim();

/* Sanity availability → the site's canonical status vocabulary. */
const STATUS = {available: 'active', coming_soon: 'coming_soon', sold_out: 'sold_out'};

async function main() {
  const products = await client.fetch(
    `*[_type == "product" && ${NOT_DRAFT}] | order(_createdAt desc){
       _id, name, "slug": slug.current, status, detail, price, material, dimensions,
       vintedUrl, leboncoinUrl, "category": category->slug.current,
       "images": images[].asset->url, description
     }`,
  );

  const items = products.map((p) => ({
    id: `sanity-${p.slug || p._id}`,
    title_fr: p.name,
    desc_fr: p.detail || blocksToText(p.description) || null,
    price: p.price ?? null,
    category: p.category || '',
    material: p.material || null,
    status: STATUS[p.status] || 'active',
    images: (p.images || []).map((u) => sized(u)).filter(Boolean),
    img: sized((p.images || [])[0]),
    source_url: p.vintedUrl || p.leboncoinUrl || null,
  }));

  writeJson(path.join(DATA_DIR, 'sanity.json'), {source: 'sanity', count: items.length, items});

  const [settings, homepage, impact, faqs] = await Promise.all([
    client.fetch(`*[_type == "siteSettings" && ${NOT_DRAFT}][0]`),
    client.fetch(
      `*[_type == "homepage" && ${NOT_DRAFT}][0]{
         heroEyebrow, heroTitle, heroLede, sections,
         "heroImage": heroImage.asset->url,
         "featured": featured[]->{name, "slug": slug.current}
       }`,
    ),
    client.fetch(`*[_type == "impact" && ${NOT_DRAFT}][0]`),
    client.fetch(`*[_type == "faq" && ${NOT_DRAFT}] | order(order asc){question, answer}`),
  ]);

  writeJson(path.join(DATA_DIR, 'content.json'), {
    settings: settings || {},
    homepage: homepage ? {...homepage, heroImage: sized(homepage.heroImage, 1200)} : {},
    impact: impact || {},
    faqs: (faqs || []).map((f) => ({question: f.question, answer: blocksToText(f.answer)})),
  });

  console.log(`fetch-sanity: ${items.length} product(s) → data/sanity.json; content.json written.`);
}

main().catch((e) => {
  console.error(`fetch-sanity failed: ${e.message}`);
  process.exit(1);
});
