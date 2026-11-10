import { readFileSync } from 'node:fs';
import { defineConfig } from 'vite';

// The display name of the noise lives in names.json; %name% and %short%
// in the HTML pages are replaced from it at build time.
const names = JSON.parse( readFileSync( new URL( './names.json', import.meta.url ) ) );

export default defineConfig( {
	root: 'site',
	base: '/houston-stratified-noise/', // GitHub Pages project site
	plugins: [ { name: 'names', transformIndexHtml: ( html ) => html.replace( /%(\w+)%/g, ( match, key ) => names[ key ] ?? match ) } ],
	server: { fs: { allow: [ '..' ] } },
	build: {
		outDir: '../dist',
		emptyOutDir: true,
		rollupOptions: { input: [ 'site/index.html', 'site/results.html', 'site/explorer.html' ] }
	}
} );
