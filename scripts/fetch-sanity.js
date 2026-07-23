/* ============================================================================
   Sanity → static site bridge  (Phase 2)
   ----------------------------------------------------------------------------
   Fetches PUBLISHED content from Sanity and writes:
     data/sanity.json   → products in the manual-source shape, so sync-catalog.js
                          normalizes/dedupes/timestamps them like every other source.
     data/content.json  → homepage, impact, FAQ, site settings (for page rendering).

   Runs at build time (Cloudflare Pages) and locally. Needs the Sanity project
   id: SANITY_PROJECT_ID, or the Studio's SANITY_STUDIO_PROJECT_ID (read from
   studio/.env locally via loadEnv). When neither is set, this exits 0 and
   writes nothing, so the site still builds from the existing manual sources.
   A SANITY_API_TOKEN is only needed for private/draft content — published
   content is public and served from the CDN without one.
   ========================================================================== */
import path from 'node:path';
import {DATA_DIR, writeJson} from './lib/normalize.js';
import {loadEnv} from './lib/env.js';

loadEnv();
const projectId = process.env.SANITY_PROJECT_ID || process.env.SANITY_STUDIO_PROJECT_ID;
const dataset = process.env.SANITY_DATASET || process.env.SANITY_STUDIO_DATASET || 'production';
const token = process.env.SANITY_API_TOKEN;

if (!projectId) {
  console.log('fetch-sanity: no SANITY_PROJECT_ID / SANITY_STUDIO_PROJECT_ID — skipping (no Sanity source yet).');
  process.exit(0);
}

// Imported dynamically so the build works even before `npm install` adds the dep.
const {createClient} = await import('@sanity/client');
// useCdn:false — builds must read live, so a publish-triggered rebuild never
// fetches a stale (cached) value of the edit that triggered it.
// token is passed only when set (needed for a private dataset / drafts).
const client = createClient({
  projectId,
  dataset,
  apiVersion: '2024-01-01',
  useCdn: false,
  ...(token ? {token} : {}),
});

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

/* Sanity availability (schema: available|coming_soon|sold_out) → the vocabulary
   boutique.html actually renders: 'active' (buyable), 'soon' (Bientôt tag),
   'sold' (Vendu tag). Keep these values in step with the checks in boutique.html. */
const STATUS = {available: 'active', coming_soon: 'soon', sold_out: 'sold'};

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

/* Sanity being unreachable is NOT a build failure: the site is designed to fall
   back to the committed manual sources (see header). A missing/private dataset —
   e.g. the CMS isn't set up yet — is the expected "skip" case; any other fetch
   error (network blip, GROQ change) is also non-fatal so a 15-min cron can't spam
   failures or block a deploy. We DON'T write sanity.json on error, so the last
   good copy stays in place and sync-catalog uses it. */
main().catch((e) => {
  const missing = /not found/i.test(e.message);
  console.warn(
    missing
      ? `fetch-sanity: dataset "${dataset}" not found for project "${projectId}" — CMS not reachable, building from existing sources. (${e.message})`
      : `fetch-sanity: fetch failed — building from existing sources instead. (${e.message})`,
  );
  process.exit(0);
});
