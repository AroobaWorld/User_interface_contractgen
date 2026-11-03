/** @type {import('tailwindcss').Config} */
export default {
  // The dashboard turns dark mode on by adding a "dark" class to its root.
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
