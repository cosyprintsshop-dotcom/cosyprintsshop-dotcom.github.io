import {defineCliConfig} from 'sanity/cli'

export default defineCliConfig({
  api: {
    projectId: process.env.SANITY_STUDIO_PROJECT_ID,
    dataset: process.env.SANITY_STUDIO_DATASET || 'production',
  },
  // The subdomain for the hosted editor: https://cosyprints.sanity.studio
  studioHost: 'cosyprints',
  deployment: {
    appId: 'wq1s5uinm1fvt5yj73rfwjb7',
  },
})
