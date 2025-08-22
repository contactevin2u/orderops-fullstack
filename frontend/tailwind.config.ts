import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./pages/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}', './styles/**/*.css'],
  theme: {
    extend: {
      colors: {
        brand: { 50: '#f3f8ff', 100: '#e6f0ff', 500: '#3b82f6', 600: '#2563eb' },
        accent: { 500: '#f59e0b', 600: '#d97706' },
        success: { 500: '#16a34a' },
        warning: { 500: '#f59e0b' },
        danger: { 500: '#ef4444' },
        ink: { 900: '#0b1220', 600: '#445069', 400: '#6b7280', 200: '#e5e7eb' },
      },
      spacing: {
        1: '4px',
        2: '8px',
        3: '12px',
        4: '16px',
        6: '24px',
        8: '32px',
      },
      borderRadius: {
        lg: '12px',
        xl: '16px',
      },
    },
  },
  plugins: [],
};

export default config;
