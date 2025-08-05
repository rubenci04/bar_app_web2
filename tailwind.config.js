/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        'brand': {
          'background': '#1e293b',
          'surface': '#334155',
          'primary': '#f59e0b',
          'primary-hover': '#fde047',
        },
        'text': {
          'primary': '#f1f5f9',
          'secondary': '#94a3b8',
        }
      }
    },
  },
  plugins: [],
}