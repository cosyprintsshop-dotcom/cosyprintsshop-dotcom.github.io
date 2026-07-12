/* One-off seed, run via the logged-in CLI session (no token needed):
     npx sanity exec seed.mjs --with-user-token
   Mirrors today's live site into Sanity. Idempotent (fixed _ids + hash-deduped
   image uploads). Kept in sync with ../scripts/seed-sanity.js. */
import fs from 'node:fs'
import path from 'node:path'
import {getCliClient} from 'sanity/cli'

const client = getCliClient({apiVersion: '2024-01-01'})
const IMG_DIR = path.resolve('..', 'assets', 'img')

const uploadCache = new Map()
async function image(file, key) {
  if (!uploadCache.has(file)) {
    const buf = fs.readFileSync(path.join(IMG_DIR, file))
    const asset = await client.assets.upload('image', buf, {filename: file})
    uploadCache.set(file, asset._id)
    console.log(`  uploaded ${file}`)
  }
  const ref = {_type: 'image', asset: {_type: 'reference', _ref: uploadCache.get(file)}}
  return key ? {...ref, _key: key} : ref
}

const richText = (text, key = 'a') => [
  {_type: 'block', _key: key, style: 'normal', markDefs: [], children: [{_type: 'span', _key: key + 's', text, marks: []}]},
]

const CATEGORIES = [
  ['homie-vibe', 'Homie Vibe', 'cat-cuisine.jpg', 1],
  ['lampes', 'Lumière & Lampes', 'cat-luminaires.jpg', 2],
  ['cable-management', 'Cable Management', 'cat-animaux.jpg', 3],
  ['bureau', 'Bureau & Rangement', 'cat-rangement.jpg', 4],
  ['gadgets', 'Gadgets Utiles', null, 5],
]

const PRODUCTS = [
  ['corbeille-onde', 'Corbeille Onde', 'Olive mat · Taille L', 'homie-vibe', 'prod-corbeille.jpg'],
  ['lampe-prisme', 'Lampe Prisme', 'Blanc cassé · LED incluse', 'lampes', 'prod-lampe.jpg'],
  ['pateres-galet', 'Lot de 3 Patères Galet', 'Sauge mat · Fixations incluses', 'homie-vibe', 'prod-pateres.jpg'],
  ['cache-pot-dune', 'Cache-pot Dune', 'Sable · Ø 15 cm', 'homie-vibe', 'prod-cachepot.jpg'],
]

const FAQS = [
  ['Qu’est-ce que le PLA ?', 'Le PLA (acide polylactique) est une matière plastique d’origine végétale, généralement issue de l’amidon de maïs. Il est biosourcé, renouvelable et biodégradable en conditions industrielles.'],
  ['Les objets sont-ils résistants ?', 'Nos pièces sont conçues pour un usage décoratif et utilitaire quotidien. Le PLA offre une excellente rigidité. Évitez toutefois les températures supérieures à 50 °C (pas de lave-vaisselle).'],
  ['Quels sont les délais de fabrication ?', 'Chaque pièce est imprimée à la demande. Comptez 3 à 5 jours ouvrés pour la fabrication, puis quelques jours d’expédition via Mondial Relay.'],
  ['Comment se passent le paiement et la livraison ?', 'Tout passe par Vinted ou Leboncoin : paiement et livraison protégés par les plateformes, sans créer de compte chez nous. Remise en main propre possible autour de Grenoble.'],
  ['Comment entretenir mes objets ?', 'Un chiffon doux légèrement humide suffit. Évitez les produits abrasifs, l’exposition prolongée au soleil et les sources de chaleur directe.'],
]

async function main() {
  console.log('Seeding categories…')
  for (const [slug, name, img, order] of CATEGORIES) {
    await client.createOrReplace({
      _id: `category-${slug}`, _type: 'category', name,
      slug: {_type: 'slug', current: slug}, order,
      ...(img ? {image: await image(img)} : {}),
    })
  }

  console.log('Seeding products…')
  const featured = []
  for (const [slug, name, detail, cat, img] of PRODUCTS) {
    const _id = `product-${slug}`
    await client.createOrReplace({
      _id, _type: 'product', name, slug: {_type: 'slug', current: slug},
      status: 'coming_soon', detail,
      category: {_type: 'reference', _ref: `category-${cat}`},
      images: [await image(img, 'cover')],
    })
    featured.push({_type: 'reference', _ref: _id, _key: slug})
  }

  console.log('Seeding FAQ…')
  for (let i = 0; i < FAQS.length; i++) {
    const [question, answer] = FAQS[i]
    await client.createOrReplace({_id: `faq-${i + 1}`, _type: 'faq', question, answer: richText(answer, `faq${i + 1}`), order: i + 1})
  }

  console.log('Seeding singletons…')
  await client.createOrReplace({
    _id: 'impact', _type: 'impact', percentage: 40,
    causes: [
      {_key: 'cancer', title: 'Recherche contre le cancer', body: '20 % de chaque vente finance la recherche contre le cancer, en mémoire de ceux qu’on a perdus.', share: 20},
      {_key: 'ocean', title: 'Dépollution des océans', body: '20 % finance des initiatives certifiées de collecte du plastique en mer — parce que notre matière vient de la terre.', share: 20},
    ],
    donationsRaised: 0, plasticRemoved: 0,
  })

  await client.createOrReplace({
    _id: 'siteSettings', _type: 'siteSettings', contactEmail: 'cosyprints.shop@gmail.com',
    social: {
      vinted: 'https://www.vinted.fr/member/60879390-cosyprints',
      leboncoin: 'https://www.leboncoin.fr/profil/0408d333-46e3-4487-b2f3-4743fd34c872',
    },
  })

  await client.createOrReplace({
    _id: 'homepage', _type: 'homepage',
    heroEyebrow: 'Atelier près de Grenoble — Imprimé à la demande',
    heroTitle: 'Le beau, utile et raisonné.',
    heroLede: 'Des objets de maison en PLA végétal, dessinés et imprimés à la demande dans notre atelier de Saint-Martin-d’Uriage. Pour un quotidien plus doux, sans surstock ni compromis.',
    heroImage: await image('hero-vase.jpg'),
    featured,
    sections: {categories: true, demarche: true, atelier: true, engagement: true, faq: true},
  })

  console.log(`\nDone — ${CATEGORIES.length} categories, ${PRODUCTS.length} products, ${FAQS.length} FAQ, impact, settings, homepage.`)
}

main().then(() => process.exit(0)).catch((e) => { console.error(`seed failed: ${e.message}`); process.exit(1) })
