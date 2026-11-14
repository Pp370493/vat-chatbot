/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        rd: {
          blue: "#0A2540",
          accent: "#0066CC",
          gold: "#D4AF37",
          light: "#F4F7FC",
        },
      },
    },
  },
  plugins: [],
};
