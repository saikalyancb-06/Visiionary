/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f4ff',
          100: '#e0e9ff',
          500: '#4f6ef7',
          600: '#3b57e8',
          700: '#2e45d0',
          900: '#1a2a8a',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'flow': 'flow 2s ease-in-out infinite',
        'scan': 'scan 2.5s ease-in-out infinite',
      },
      keyframes: {
        flow: {
          '0%, 100%': { opacity: '0.4', transform: 'translateX(-4px)' },
          '50%': { opacity: '1', transform: 'translateX(4px)' },
        },
        scan: {
          '0%': { top: '0%' },
          '100%': { top: '100%' },
        },
      },
    },
  },
  plugins: [],
}
