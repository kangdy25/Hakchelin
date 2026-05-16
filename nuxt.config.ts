export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',

  devtools: { enabled: true },

  modules: [
    '@nuxtjs/tailwindcss',
    '@nuxtjs/supabase',
    '@pinia/nuxt',
    '@nuxtjs/i18n'
  ],

  supabase: {
    redirect: false
  },

  i18n: {
    strategy: 'no_prefix',

    defaultLocale: 'ko',

    detectBrowserLanguage: false,

    locales: [
      {
        code: 'ko',
        file: 'ko.ts',
        name: 'Korean'
      },
      {
        code: 'en',
        file: 'en.ts',
        name: 'English'
      }
    ],

    langDir: 'locales',

    vueI18n: './i18n.config.ts'
  }
})