import {defineConfig} from 'sanity'
import {structureTool} from 'sanity/structure'
import {visionTool} from '@sanity/vision'
import {schemaTypes} from './schemas'
import {structure} from './structure'

// projectId is written by `npx sanity init` into .env (SANITY_STUDIO_PROJECT_ID).
const projectId = process.env.SANITY_STUDIO_PROJECT_ID || ''
const dataset = process.env.SANITY_STUDIO_DATASET || 'production'

// Types that must exist exactly once — no "create" / no "delete" in the UI.
const SINGLETON_TYPES = new Set(['homepage', 'impact', 'siteSettings'])
const SINGLETON_ACTIONS = new Set(['publish', 'discardChanges', 'restore'])

export default defineConfig({
  name: 'default',
  title: 'CosyPrints',
  projectId,
  dataset,
  plugins: [structureTool({structure}), visionTool()],
  schema: {
    types: schemaTypes,
    // Hide singletons from the global "create new document" menu.
    templates: (templates) => templates.filter((t) => !SINGLETON_TYPES.has(t.schemaType)),
  },
  document: {
    // Remove delete/duplicate from singletons so editors can't break structure.
    actions: (input, {schemaType}) =>
      SINGLETON_TYPES.has(schemaType)
        ? input.filter(({action}) => action && SINGLETON_ACTIONS.has(action))
        : input,
  },
})
