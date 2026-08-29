// @ts-check
import { defineConfig } from 'astro/config';

import react from '@astrojs/react';

// https://astro.build/config
export default defineConfig({
  site: 'https://euisuk-chung.github.io',
  base: process.env.GITHUB_ACTIONS ? '/Stocks-tracker' : '/',
  integrations: [react()]
});
