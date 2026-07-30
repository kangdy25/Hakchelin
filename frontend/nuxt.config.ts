export default defineNuxtConfig({
  compatibilityDate: "2025-07-15",

  devtools: { enabled: true },

  app: {
    head: {
      title: "학슐랭 - 대학생 맞춤형 스마트 학식 시스템",
      meta: [
        { charset: "utf-8" },
        { name: "viewport", content: "width=device-width, initial-scale=1" },
        { name: "description", content: "대학생 맞춤형 스마트 학식 시스템 학슐랭(Hakchelin)" },
        // Open Graph
        { property: "og:title", content: "학슐랭 - 대학생 맞춤형 스마트 학식 시스템" },
        {
          property: "og:description",
          content: "사전 예약 및 맞춤형 옵션 선택으로 편리하고 개인화된 식사 경험을 제공하는 스마트 학식 시스템 학슐랭"
        },
        { property: "og:image", content: "/Hakchelin.jpeg" },
        { property: "og:type", content: "website" },
        // Twitter Card
        { name: "twitter:card", content: "summary_large_image" },
        { name: "twitter:title", content: "학슐랭 - 대학생 맞춤형 스마트 학식 시스템" },
        {
          name: "twitter:description",
          content: "사전 예약 및 맞춤형 옵션 선택으로 편리하고 개인화된 식사 경험을 제공하는 스마트 학식 시스템 학슐랭"
        },
        { name: "twitter:image", content: "/Hakchelin.jpeg" }
      ],
      link: [{ rel: "icon", type: "image/x-icon", href: "/favicon.ico" }]
    }
  },

  runtimeConfig: {
    public: {
      tossPaymentsClientKey: process.env.NUXT_PUBLIC_TOSS_PAYMENTS_CLIENT_KEY || "",
      apiBaseUrl:
        process.env.NUXT_PUBLIC_API_BASE_URL ||
        (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "")
    }
  },

  modules: ["@nuxtjs/tailwindcss", "@nuxtjs/i18n"],

  i18n: {
    // langDir을 프로젝트 루트 기준으로 해석해 locales/만 단일 원본으로 사용한다.
    restructureDir: ".",

    strategy: "no_prefix",

    defaultLocale: "ko",

    detectBrowserLanguage: false,

    locales: [
      {
        code: "ko",
        file: "ko.ts",
        name: "Korean"
      },
      {
        code: "en",
        file: "en.ts",
        name: "English"
      }
    ],

    langDir: "locales",

    vueI18n: "./i18n.config.ts"
  }
});
