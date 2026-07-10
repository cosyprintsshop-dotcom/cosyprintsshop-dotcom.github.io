import {defineType, defineField} from 'sanity'

/** Singleton — donation & impact transparency, shown on the homepage + engagement page. */
export default defineType({
  name: 'impact',
  title: 'Dons & impact',
  type: 'document',
  fields: [
    defineField({
      name: 'percentage',
      title: '% reversé par vente',
      type: 'number',
      initialValue: 40,
      validation: (r) => r.required().min(0).max(100),
    }),
    defineField({
      name: 'causes',
      title: 'Causes soutenues',
      type: 'array',
      of: [
        {
          type: 'object',
          fields: [
            {name: 'title', title: 'Titre', type: 'string'},
            {name: 'body', title: 'Description', type: 'text', rows: 2},
            {name: 'share', title: 'Part (%)', type: 'number'},
          ],
          preview: {select: {title: 'title', subtitle: 'share'}},
        },
      ],
    }),
    defineField({
      name: 'donationsRaised',
      title: 'Dons cumulés (€)',
      type: 'number',
      initialValue: 0,
      validation: (r) => r.min(0),
    }),
    defineField({
      name: 'plasticRemoved',
      title: 'Plastique retiré (g)',
      type: 'number',
      initialValue: 0,
      validation: (r) => r.min(0),
    }),
    defineField({name: 'lastUpdated', title: 'Mis à jour le', type: 'date'}),
    defineField({name: 'note', title: 'Note de transparence', type: 'text', rows: 2}),
  ],
  preview: {prepare: () => ({title: 'Dons & impact'})},
})
