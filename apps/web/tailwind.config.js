/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#82d695',
          light: '#9be0ab',
          dark: '#68ab77',
        },
        accent: '#00f0ff',
        surface: {
          DEFAULT: '#1a1d1c',
          page: '#121413',
          overlay: '#1e2120',
          raised: '#242827',
        },
        border: {
          DEFAULT: '#2a2e2d',
          light: '#242827',
        },
        text: {
          primary: '#ffffff',
          secondary: '#a0aab2',
          muted: '#717a82',
        },
        status: {
          success: '#82d695',
          warning: '#faad14',
          danger: '#ff4d4f',
          info: '#717a82',
        },
      },
    },
  },
  plugins: [],
}
