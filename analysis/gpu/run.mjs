// Drives the installed Google Chrome (headless, hardware Metal WebGPU) through the harness pages.
// usage: node analysis/gpu/run.mjs analysis/gpu/jobs-realtime.json   job = { tree, page, query, name, warmup, frames, fps }
// Needs puppeteer (`pnpm dlx` or a local install; it is not a dependency of this repository) and the three
// worktrees served on the ports below (see README.md). Output goes to analysis/gpu/raw, or $GPU_RAW.
import puppeteer from 'puppeteer';
import fs from 'node:fs';
import path from 'node:path';

const PORTS = { base: 8131, head: 8132, bake: 8133 };
const OUT = path.resolve( process.env.GPU_RAW ?? 'analysis/gpu/raw' );
const jobs = JSON.parse( fs.readFileSync( process.argv[ 2 ], 'utf8' ) );

const browser = await puppeteer.launch( {
	executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
	headless: true,
	protocolTimeout: 0,
	args: [ '--enable-unsafe-webgpu', '--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', '--disable-frame-rate-limit', '--disable-gpu-vsync', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--window-size=1100,900' ]
} );

for ( const job of jobs ) {

	const dir = path.join( OUT, job.dir );
	fs.mkdirSync( dir, { recursive: true } );
	const jsonPath = path.join( dir, job.name + '.json' );
	if ( fs.existsSync( jsonPath ) && ! process.env.FORCE ) { console.log( 'skip', job.name ); continue; }

	const page = await browser.newPage();
	page.on( 'console', ( m ) => { if ( m.type() === 'error' || m.type() === 'warn' ) console.log( '  [page]', m.text().slice( 0, 400 ) ); } );
	page.on( 'pageerror', ( e ) => console.log( '  [pageerror]', e.message ) );
	await page.exposeFunction( '__save', ( name, b64 ) => fs.writeFileSync( path.join( dir, name ), Buffer.from( b64, 'base64' ) ) );
	await page.goto( `http://localhost:${ PORTS[ job.tree ] }/examples/${ job.page }?${ job.query ?? '' }` );
	await page.waitForFunction( 'window.__ready === true', { timeout: 120000 } );

	const adapter = await page.evaluate( 'window.__adapter' );
	if ( adapter.isFallbackAdapter === true || ! /apple|nvidia|amd|intel/i.test( adapter.vendor ) || /swiftshader|llvmpipe|lavapipe/i.test( JSON.stringify( adapter ) ) ) throw new Error( 'not a hardware adapter: ' + JSON.stringify( adapter ) );

	let result;
	if ( job.fps ) result = await page.evaluate( ( s ) => window.__throughput( s ), job.fps );
	else if ( job.call ) result = await page.evaluate( ( c, o ) => window[ c ]( o ), job.call, { name: job.name, ...job.options } );
	else result = await page.evaluate( ( o ) => window.__capture( o ), { name: job.name, warmup: job.warmup, frames: job.frames } );

	fs.writeFileSync( jsonPath, JSON.stringify( { job, adapter, chrome: await browser.version(), result }, null, '\t' ) );
	console.log( job.dir, job.name, JSON.stringify( result ).slice( 0, 300 ), JSON.stringify( adapter ).slice( 0, 120 ) );
	await page.close();

}

await browser.close();
