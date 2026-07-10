import {defineType, defineField} from 'sanity'

/** Singleton — homepage hero, featured products (ordered), section toggles. */
export default defineType({
  name: 'homepage',
  title: 'Page d’accueil',
  type: 'document',
  fields: [
    defineField({name: 'heroEyebrow', title: 'Hero — sur-titre', type: 'string'}),
    defineField({name: 'heroTitle', title: 'Hero — titre', type: 'string'}),
    defineField({name: 'heroLede', title: 'Hero — texte', type: 'text', rows: 3}),
    defineField({name: 'heroImage', title: 'Hero — image', type: 'image', options: {hotspot: true}}),
    defineField({
      name: 'featured',
      title: 'Produits mis en avant',
      type: 'array',
      of: [{type: 'reference', to: [{type: 'product'}]}],
      description: 'Glissez pour réordonner. Ces produits apparaissent sur la page d’accueil.',
      validation: (r) => r.max(8),
    }),
    defineField({
      name: 'sections',
      title: 'Sections visibles',
      type: 'object',
      options: {collapsible: true},
      fields: [
        {name: 'categories', title: 'Catégories', type: 'boolean', initialValue: true},
        {name: 'demarche', title: 'Notre démarche', type: 'boolean', initialValue: true},
        {name: 'atelier', title: 'L’atelier', type: 'boolean', initialValue: true},
        {name: 'engagement', title: 'Notre engagement', type: 'boolean', initialValue: true},
        {name: 'faq', title: 'FAQ', type: 'boolean', initialValue: true},
      ],
    }),
  ],
  preview: {prepare: () => ({title: 'Page d’accueil'})},
})
