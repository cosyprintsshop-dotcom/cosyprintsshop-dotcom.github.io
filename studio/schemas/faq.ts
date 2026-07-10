import {defineType, defineField} from 'sanity'

export default defineType({
  name: 'faq',
  title: 'FAQ',
  type: 'document',
  fields: [
    defineField({name: 'question', title: 'Question', type: 'string', validation: (r) => r.required()}),
    defineField({
      name: 'answer',
      title: 'Réponse',
      type: 'array',
      of: [{type: 'block'}],
      validation: (r) => r.required(),
    }),
    defineField({name: 'order', title: 'Ordre', type: 'number', initialValue: 0}),
  ],
  orderings: [{title: 'Ordre', name: 'order', by: [{field: 'order', direction: 'asc'}]}],
  preview: {select: {title: 'question', subtitle: 'order'}},
})
