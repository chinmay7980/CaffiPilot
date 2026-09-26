/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#07090e',
          800: '#0d111c',
          700: '#161d2f',
          600: '#232d45',
        },
        brand: {
          blue: '#3b82f6',
          purple: '#8b5cf6',
          cyan: '#06b6d4',
        }
      }
    },
  },
  plugins: [],
};
