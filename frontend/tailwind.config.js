/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1e293b",
        panel: "#f8fafc",
      },
    },
  },
  plugins: [],
};
