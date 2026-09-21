import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg:       '#0A0A0A',
        surface:  '#111111',
        card:     '#161616',
        border:   '#252525',
        muted:    '#777777',
        accent:   '#DFFF00',
        danger:   '#FF3B30',
        success:  '#30D158',
        warning:  '#FF9F0A',
        whatsapp: '#25D366',
      },
      fontFamily: {
        sans: ["'Space Grotesk'", "'Inter'", 'system-ui', 'sans-serif'],
        mono: ["'Space Mono'", 'monospace'],
      },
      borderRadius: {
        none: '0px',
        sm:   '2px',
        DEFAULT: '4px',
        md:   '4px',
      },
    },
  },
  plugins: [],
} satisfies Config
