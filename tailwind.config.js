// Archivo: tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        'brand': {
          'background': '#1a202c', // Nuevo color de fondo principal
          'surface': '#2d3748',    // Nuevo color para tarjetas y contenedores
          'primary': '#e2e8f0',    // Nuevo color para texto principal
          'secondary': '#a0aec0',  // Nuevo color para texto secundario
        },
        'accent': {
            'blue': '#3182ce',     // Azul para acentos
            'blue-dark': '#2c5282',
            'green': '#38a169',
            'green-dark': '#2f855a',
            'red': '#e53e3e',
            'red-dark': '#c53030',
        },
        // Definición de una paleta de colores más suave y consistente
        'gray': {
          '50': '#f8fafc',
          '100': '#f1f5f9',
          '200': '#e2e8f0',
          '300': '#cbd5e1',
          '400': '#94a3b8',
          '500': '#64748b',
          '600': '#475569',
          '700': '#334155',
          '800': '#1e293b',
          '900': '#0f172a',
          '950': '#0d1320',
        },
        'blue': {
            '50': '#eff6ff',
            '100': '#dbeafe',
            '200': '#bfdbfe',
            '300': '#93c5fd',
            '400': '#60a5fa',
            '500': '#3b82f6',
            '600': '#2563eb',
            '700': '#1d4ed8',
            '800': '#1e40af',
            '900': '#1e3a8a',
            '950': '#172b4d',
        },
        'amber': {
            '50': '#fffbeb',
            '100': '#fef3c7',
            '200': '#fde68a',
            '300': '#fcd34d',
            '400': '#fbbf24',
            '500': '#f59e0b',
            '600': '#d97706',
            '700': '#b45309',
            '800': '#92400e',
            '900': '#78350f',
            '950': '#451a03',
        },
        'emerald': {
            '50': '#ecfdf5',
            '100': '#d1fae5',
            '200': '#a7f3d0',
            '300': '#6ee7b7',
            '400': '#34d399',
            '500': '#10b981',
            '600': '#059669',
            '700': '#047857',
            '800': '#065f46',
            '900': '#064e3b',
            '950': '#022c22',
        },
        'red': {
            '50': '#fef2f2',
            '100': '#fee2e2',
            '200': '#fecaca',
            '300': '#fca5a5',
            '400': '#f87171',
            '500': '#ef4444',
            '600': '#dc2626',
            '700': '#b91c1c',
            '800': '#991b1b',
            '900': '#7f1d1d',
            '950': '#450a0a',
        },
      }
    },
  },
  plugins: [],
}