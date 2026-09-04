/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0b0d12",
          900: "#12141a",
          800: "#1a1d24",
          700: "#242832",
          600: "#323744",
        },
        mist: {
          100: "#eef0f3",
          300: "#c2c8d2",
          500: "#8b93a1",
        },
        signal: {
          DEFAULT: "#ffb238",
          dim: "#a67526",
        },
        ok: "#4ade80",
        bad: "#f87171",
      },
      fontFamily: {
        display: ["Space Grotesk", "sans-serif"],
        body: ["Inter", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
    },
  },
  plugins: [],
}
