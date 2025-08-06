/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        'brand': {
          'background': '#1e293b', // Gris-azulado oscuro
          'surface': '#334155',    // Gris para tarjetas y contenedores
          'primary': '#f59e0b',    // Ámbar cálido para botones y acentos
          'primary-hover': '#fde047', // Amarillo para el hover
        },
        'text': {
          'primary': '#f1f5f9',    // Gris muy claro (casi blanco)
          'secondary': '#94a3b8',  // Gris suave para texto secundario
        }
      }
    },
  },
  plugins: [],
}
