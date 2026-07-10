import {defineType, defineField} from 'sanity'

/**
 * Category slugs MUST match the CATEGORIES list in scripts/lib/normalize.js
 * and boutique.html: homie-vibe, cable-management, lampes, bureau, gadgets.
 */
export default defineType({
  name: 'category',
  title: 'Catégorie',
  type: 'document',
  fields: [
    defineField({name: 'name', title: 'Nom', type: 'string', validation: (r) => r.required()}),
    defineField({
      name: 'slug',
      title: 'Identifiant URL',
      type: 'slug',
      options: {source: 'name', maxLength: 60},
      description: 'Doit correspondre aux catégories de la boutique (homie-vibe, lampes, bureau…).',
      validation: (r) => r.required(),
    }),
    defineField({name: 'image', title: 'Image', type: 'image', options: {hotspot: true}}),
    defineField({name: 'order', title: 'Ordre d’affichage', type: 'number', initialValue: 0}),
  ],
  orderings: [{title: 'Ordre', name: 'order', by: [{field: 'order', direction: 'asc'}]}],
  preview: {select: {title: 'name', subtitle: 'slug.current', media: 'image'}},
})
