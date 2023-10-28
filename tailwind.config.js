/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["templates/**/*.html"],
  theme: {
    extend: {
      width: {
        128: "32rem",
      },
    },
  },
};
