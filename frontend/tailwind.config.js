/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/forms')
  ],
  safelist: [
    // Add status colors
    'bg-green-100', 'text-green-800',
    'bg-yellow-100', 'text-yellow-800',
    'bg-red-100', 'text-red-800',
    'bg-blue-100', 'text-blue-800',
    'bg-purple-100', 'text-purple-800',
    'bg-gray-100', 'text-gray-800',
    // Add button state colors
    'bg-indigo-500', 'bg-indigo-600', 'bg-indigo-700',
    'hover:bg-indigo-500', 'hover:bg-indigo-700',
    'bg-indigo-300', 'bg-gray-50', 'hover:bg-gray-50',
    // Add transform and animation classes
    'transform', 'transition-all', 'transition-shadow',
    'hover:shadow-md', 'animate-spin'
  ],
}
