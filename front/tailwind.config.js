/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'apple-blue': '#007aff',
        'apple-gray': '#86868b',
        'apple-dark': '#1d1d1f',
        'apple-bg': '#f5f5f7',
      },
      fontFamily: {
        'sans': ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', 'Arial', 'sans-serif'],
        'mono': ['SF Mono', 'Monaco', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}
