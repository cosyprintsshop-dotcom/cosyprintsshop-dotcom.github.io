import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'product',
  title: 'Produit',
  type: 'document',
  fields: [
    defineField({
      name: 'name',
      title: 'Nom',
      type: 'string',
      validation: (r) => r.required(),
    }),
    defineField({
      name: 'slug',
      title: 'Identifiant URL',
      type: 'slug',
      options: {source: 'name', maxLength: 60},
      validation: (r) => r.required(),
    }),
    defineField({
      name: 'status',
      title: 'Disponibilité',
      type: 'string',
      options: {
        layout: 'radio',
        list: [
          {title: 'Disponible', value: 'available'},
          {title: 'Bientôt', value: 'coming_soon'},
          {title: 'Épuisé', value: 'sold_out'},
        ],
      },
      initialValue: 'coming_soon',
      validation: (r) => r.required(),
    }),
    defineField({
      name: 'category',
      title: 'Catégorie',
      type: 'reference',
      to: [{type: 'category'}],
    }),
    defineField({
      name: 'detail',
      title: 'Détail court',
      type: 'string',
      description: 'Court descriptif sous le nom — ex. « Olive mat · Taille L »',
    }),
    defineField({
      name: 'price',
      title: 'Prix (€)',
      type: 'number',
      description: 'Laisser vide tant que le produit n’est pas en vente (affiche « Bientôt »).',
      validation: (r) => r.min(0),
    }),
    defineField({
      name: 'images',
      title: 'Photos',
      type: 'array',
      of: [{type: 'image', options: {hotspot: true}}],
      options: {layout: 'grid'},
      description: 'La première photo sert de couverture. Glissez pour réordonner.',
      validation: (r) =>
        r.custom((imgs, ctx) =>
          (ctx.document?.status as string) === 'available' && (!imgs || imgs.length === 0)
            ? 'Une photo est requise pour un produit « Disponible ».'
            : true,
        ),
    }),
    defineField({
      name: 'description',
      title: 'Description',
      type: 'array',
      of: [{type: 'block'}],
    }),
    defineField({name: 'material', title: 'Matière / finition', type: 'string'}),
    defineField({name: 'dimensions', title: 'Dimensions', type: 'string'}),
    defineField({
      name: 'vintedUrl',
      title: 'Lien Vinted',
      type: 'url',
      description: 'Lien de l’annonce Vinted (le parcours d’achat actuel).',
    }),
    defineField({name: 'leboncoinUrl', title: 'Lien Leboncoin', type: 'url'}),
  ],
  orderings: [
    {title: 'Plus récent', name: 'createdDesc', by: [{field: '_createdAt', direction: 'desc'}]},
    {title: 'Nom (A→Z)', name: 'nameAsc', by: [{field: 'name', direction: 'asc'}]},
  ],
  preview: {
    select: {title: 'name', subtitle: 'status', media: 'images.0'},
    prepare({title, subtitle, media}) {
      const labels: Record<string, string> = {
        available: 'Disponible',
        coming_soon: 'Bientôt',
        sold_out: 'Épuisé',
      }
      return {title, subtitle: labels[subtitle as string] || subtitle, media}
    },
  },
})
