import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://mcp-ynab.com',
  vite: {
    plugins: [tailwindcss()],
  },
});
