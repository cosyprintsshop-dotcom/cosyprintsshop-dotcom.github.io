import type {StructureResolver} from 'sanity/structure'

/** Singletons: exactly one document each, opened directly (no list, no "create new"). */
const SINGLETONS = [
  {id: 'homepage', type: 'homepage', title: 'Page d’accueil'},
  {id: 'impact', type: 'impact', title: 'Dons & impact'},
  {id: 'siteSettings', type: 'siteSettings', title: 'Réglages du site'},
]

export const structure: StructureResolver = (S) =>
  S.list()
    .title('CosyPrints')
    .items([
      S.documentTypeListItem('product').title('Produits'),
      S.documentTypeListItem('category').title('Catégories'),
      S.documentTypeListItem('faq').title('FAQ'),
      S.divider(),
      ...SINGLETONS.map(({id, type, title}) =>
        S.listItem()
          .title(title)
          .id(id)
          .child(S.document().schemaType(type).documentId(id)),
      ),
    ])
