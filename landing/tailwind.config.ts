import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg:      '#0a0a0f',
        bg2:     '#0f0f1a',
        bg3:     '#141428',
        surface: '#1a1a2e',
        accent:  '#8b5cf6',
        accent2: '#06b6d4',
        accent3: '#10b981',
        warn:    '#f59e0b',
        danger:  '#ef4444',
        muted:   '#94a3b8',
      },
    },
  },
  plugins: [],
};

export default config;
