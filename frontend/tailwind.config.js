/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#0f172a",
        ink: "#0b1220",
        amber: "#f59e0b",
        green: "#22c55e",
        red: "#ef4444"
      }
    }
  },
  plugins: [require("@tailwindcss/forms")]
};
