import {defineType, defineField} from 'sanity'

/** Singleton — global site settings, announcement banner, practical info. */
export default defineType({
  name: 'siteSettings',
  title: 'Réglages du site',
  type: 'document',
  fields: [
    defineField({name: 'contactEmail', title: 'E-mail de contact', type: 'string'}),
    defineField({
      name: 'announcement',
      title: 'Bandeau d’annonce',
      type: 'object',
      options: {collapsible: true, collapsed: false},
      fields: [
        {name: 'enabled', title: 'Afficher le bandeau', type: 'boolean', initialValue: false},
        {name: 'text', title: 'Texte', type: 'string'},
        {name: 'link', title: 'Lien (optionnel)', type: 'url'},
      ],
    }),
    defineField({name: 'pickup', title: 'Retrait en main propre', type: 'text', rows: 2}),
    defineField({name: 'shipping', title: 'Livraison', type: 'text', rows: 2}),
    defineField({name: 'customOrder', title: 'Commande personnalisée', type: 'text', rows: 2}),
    defineField({
      name: 'social',
      title: 'Liens',
      type: 'object',
      options: {collapsible: true},
      fields: [
        {name: 'vinted', title: 'Vinted', type: 'url'},
        {name: 'leboncoin', title: 'Leboncoin', type: 'url'},
        {name: 'instagram', title: 'Instagram', type: 'url'},
      ],
    }),
  ],
  preview: {prepare: () => ({title: 'Réglages du site'})},
})
