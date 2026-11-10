// Renders the algorithm diagrams from the reference implementation into results/solution/*.webp.
// Run from the repository root: node analysis/solution/figures.js   (sharp rasterises the SVG)
import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';
import * as H from '../../src/noise/index.js';
const NAMES = JSON.parse( fs.readFileSync( new URL( '../../names.json', import.meta.url ) ) );
const OUT = path.join( import.meta.dirname, '../../results/solution' );
fs.mkdirSync( OUT, { recursive: true } );

const BLUE = '#2f74d0', INK = '#111111', SUB = '#555555', GRID = '#dddddd', W = 2200, SEED = 1;
const FONT = 'font-family="Helvetica Neue, Helvetica, Arial, sans-serif"';
const text = ( x, y, s, size, o = {} ) => `<text x="${x}" y="${y}" ${FONT} font-size="${size}" font-weight="${o.bold ? 700 : 400}" fill="${o.fill || INK}" text-anchor="${o.anchor || 'start'}">${s}</text>`;
const gray = ( v ) => { const g = Math.round( 255 * v ); return `rgb(${g},${g},${g})`; };
const header = ( title, sub ) => text( 52, 82, title, 38, { bold: true } ) + sub.map( ( s, i ) => text( 52, 132 + i * 36, s, 25, { fill: SUB } ) ).join( '' );
const jobs = [];
const save = ( name, height, body ) => {
	const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${height}" viewBox="0 0 ${W} ${height}"><rect width="100%" height="100%" fill="#ffffff"/>${body}</svg>`;
	jobs.push( sharp( Buffer.from( svg ) ).webp( { quality: 90 } ).toFile( path.join( OUT, name + '.webp' ) ) );
};

// a grid of cells: value(i,j) -> { v: 0..1 shade, label }
const cellGrid = ( x0, y0, n, cell, fn, o = {} ) => {
	let s = '';
	for ( let j = 0; j < n; j ++ ) for ( let i = 0; i < n; i ++ ) {
		const { v, label } = fn( i, j );
		s += `<rect x="${x0 + i * cell}" y="${y0 + j * cell}" width="${cell + 0.5}" height="${cell + 0.5}" fill="${gray( v )}"/>`;
		if ( label !== undefined ) s += text( x0 + ( i + 0.5 ) * cell, y0 + ( j + 0.5 ) * cell + cell * 0.13, label, cell * 0.36, { anchor: 'middle', fill: v > 0.5 ? '#000' : '#fff', bold: true } );
	}
	for ( const [ step, width, color ] of o.lines || [] ) for ( let k = 0; k <= n; k += step ) {
		s += `<line x1="${x0 + k * cell}" y1="${y0}" x2="${x0 + k * cell}" y2="${y0 + n * cell}" stroke="${color}" stroke-width="${width}"/><line x1="${x0}" y1="${y0 + k * cell}" x2="${x0 + n * cell}" y2="${y0 + k * cell}" stroke="${color}" stroke-width="${width}"/>`;
	}
	return s;
};

// ---- 1. the three hierarchy levels of one 8x8 tile
{
	const TX = 16, TY = 8, cell = 76, y0 = 290, xs = [ 120, 800, 1480 ];
	const panels = [
		[ 'Level 0: 2 bits. Every 2×2 block holds 0–3', 2, 30, [ [ 1, 1, '#999' ], [ 2, 5, BLUE ] ] ],
		[ 'Levels 0–1: 4 bits. Every 4×4 block holds 0–15', 4, 28, [ [ 1, 1, '#999' ], [ 4, 5, BLUE ] ] ],
		[ 'Levels 0–2: 6 bits. The 8×8 tile holds 0–63', 6, 26, [ [ 1, 1, '#999' ], [ 8, 5, BLUE ] ] ]
	];
	let s = header( 'One 8×8 tile, built two bits at a time', [ 'Each level adds a 2-bit digit. The finest level (which pixel inside its 2×2 block) supplies the most significant digit, so stratification starts at the', 'smallest scale. Numbers are the rank so far; brightness is rank ÷ its maximum. Blue outlines mark the blocks that are guaranteed to hold every value once.' ] );
	panels.forEach( ( [ title, bits, shift, lines ], p ) => {
		s += text( xs[ p ], y0 - 28, title, 27, { bold: true } );
		s += cellGrid( xs[ p ], y0, 8, cell, ( i, j ) => { const r = H.hsnRank( TX + i, TY + j, SEED ) >>> shift; return { v: r / ( ( 1 << bits ) - 1 ), label: r }; }, { lines } );
	} );
	save( 'hierarchy-levels', 960, s );
}

// ---- 2. the eight 2x2 arrangements
{
	const cell = 96, y0 = 250;
	let s = header( 'The per-block scramble picks one of eight 2×2 arrangements', [ 'A hash of the parent block supplies three bits: one swaps the orientation and two are XORed into the rank. The result is always a rotation or', 'reflection of the 2×2 Bayer cell, so ranks 0 and 1 stay on one diagonal and 2 and 3 on the other. Sixteen of the 24 possible orders never occur.' ] );
	let k = 0;
	for ( let swap = 0; swap < 2; swap ++ ) for ( let xor = 0; xor < 4; xor ++ ) {
		const x0 = 110 + k * 254;
		s += cellGrid( x0, y0, 2, cell, ( a, b ) => { const r = ( ( ( a ^ b ) << 1 ) | ( swap ? a : b ) ) ^ xor; return { v: r / 3, label: r }; }, { lines: [ [ 1, 1, '#999' ], [ 2, 4, BLUE ] ] } );
		s += text( x0 + cell, y0 + 2 * cell + 44, `swap ${swap}, xor ${xor.toString( 2 ).padStart( 2, '0' )}`, 23, { anchor: 'middle', fill: SUB } );
		if ( k === 0 ) s += text( x0 + cell, y0 + 2 * cell + 78, '(Bayer)', 23, { anchor: 'middle', fill: SUB } );
		k ++;
	}
	save( 'scramble-arrangements', 600, s );
}

// ---- 3. Bayer vs scrambled vs the full noise vs white
{
	const n = 64, cell = 7.5, y0 = 290, xs = [ 70, 590, 1110, 1630 ];
	const bayer = ( x, y ) => { let r = 0; for ( let l = 0; l < 3; l ++ ) { const a = ( x >> l ) & 1, b = ( y >> l ) & 1; r |= ( ( ( a ^ b ) << 1 ) | b ) << ( 4 - 2 * l ); } return r / 64; };
	const panels = [
		[ 'Bayer 8×8, tiled', bayer ],
		[ '+ per-block scramble', ( x, y ) => H.hsnRank( x, y, SEED ) / 4294967296 ],
		[ `+ per-tile phase = ${NAMES.short}`, ( x, y ) => H.hsn( x, y, 0, SEED ) ],
		[ 'White noise', ( x, y ) => H.pixelHash( x, y, 99 ) / 4294967296 ]
	];
	let s = header( `From ordered dither to ${NAMES.name}`, [ '64×64 pixels of each pattern. Scrambling each block breaks the Bayer lattice but leaves every tile using the same 64 values; the per-tile phase', 'then shifts each tile by its own amount. Every aligned 8×8 tile in the first three panels still contains 64 equally spaced values; white noise does not.' ] );
	panels.forEach( ( [ title, fn ], p ) => {
		s += text( xs[ p ], y0 - 28, title, 27, { bold: true } );
		s += cellGrid( xs[ p ], y0, n, cell, ( i, j ) => ( { v: fn( i, j ) } ) );
		s += `<rect x="${xs[ p ]}" y="${y0}" width="${n * cell}" height="${n * cell}" fill="none" stroke="${GRID}" stroke-width="2"/>`;
	} );
	save( 'bayer-vs-noise', 840, s );
}

// ---- 4. tile phase: values of three neighbouring tiles on the unit interval
{
	const x0 = 330, x1 = 2090, L = x1 - x0;
	let s = header( 'Each tile holds 64 equally spaced values, shifted by its own phase', [ 'The sorted values of three neighbouring 8×8 tiles on one frame. The spacing is exactly 1/64 in every tile; only the offset differs. The zoomed strip on', 'the right half shows the first eighth of the interval so the per-tile offsets are visible.' ] );
	const rows = [ [ 0, 0 ], [ 8, 0 ], [ 16, 0 ] ];
	rows.forEach( ( [ tx, ty ], r ) => {
		const y = 300 + r * 130, v = [];
		for ( let j = 0; j < 8; j ++ ) for ( let i = 0; i < 8; i ++ ) v.push( H.hsn( tx + i, ty + j, 0, SEED ) );
		s += text( 52, y + 9, `Tile (${tx / 8}, ${ty / 8})`, 27, { bold: true } );
		s += text( 52, y + 44, `offset ${( Math.min( ...v ) * 64 ).toFixed( 2 )} / 64`, 23, { fill: SUB } );
		// full interval (left half)
		const half = L / 2 - 40;
		s += `<line x1="${x0}" y1="${y}" x2="${x0 + half}" y2="${y}" stroke="#999" stroke-width="2"/>`;
		v.forEach( ( u ) => s += `<line x1="${x0 + u * half}" y1="${y - 26}" x2="${x0 + u * half}" y2="${y + 26}" stroke="${BLUE}" stroke-width="3"/>` );
		// zoom on [0,1/8)
		const zx = x0 + half + 80;
		s += `<line x1="${zx}" y1="${y}" x2="${zx + half}" y2="${y}" stroke="#999" stroke-width="2"/>`;
		for ( let k = 0; k <= 8; k ++ ) s += `<line x1="${zx + k * half / 8}" y1="${y - 34}" x2="${zx + k * half / 8}" y2="${y + 34}" stroke="${GRID}" stroke-width="2"/>`;
		v.filter( ( u ) => u < 1 / 8 ).forEach( ( u ) => s += `<circle cx="${zx + u * 8 * half}" cy="${y}" r="11" fill="${BLUE}"/>` );
		if ( r === 2 ) {
			s += text( x0, y + 76, '0', 23, { fill: SUB, anchor: 'middle' } ) + text( x0 + half, y + 76, '1', 23, { fill: SUB, anchor: 'middle' } );
			s += text( zx, y + 76, '0', 23, { fill: SUB, anchor: 'middle' } ) + text( zx + half, y + 76, '8/64', 23, { fill: SUB, anchor: 'middle' } ) + text( zx + half / 2, y + 76, 'zoom: grid lines every 1/64', 23, { fill: SUB, anchor: 'middle' } );
			s += text( x0 + half / 2, y + 76, 'all 64 values', 23, { fill: SUB, anchor: 'middle' } );
		}
	} );
	save( 'tile-phase', 700, s );
}

// ---- 5. Weyl time step for one pixel
{
	const x0 = 330, x1 = 2090, L = x1 - x0;
	let s = header( 'Over time, each pixel walks the unit interval by the golden ratio', [ 'One pixel’s values for its first 4, 8, 16 and 32 frames, numbered in frame order. Each frame adds 0.618… and wraps, so new samples keep splitting', 'the largest remaining gaps. The step is a 32-bit integer add, so the pattern is exact at any frame count and repeats only after 2³² frames.' ] );
	[ 4, 8, 16, 32 ].forEach( ( N, r ) => {
		const y = 320 + r * 130;
		s += text( 52, y + 9, `${N} frames`, 27, { bold: true } );
		s += `<line x1="${x0}" y1="${y}" x2="${x1}" y2="${y}" stroke="#999" stroke-width="2"/><line x1="${x0}" y1="${y - 20}" x2="${x0}" y2="${y + 20}" stroke="#999" stroke-width="2"/><line x1="${x1}" y1="${y - 20}" x2="${x1}" y2="${y + 20}" stroke="#999" stroke-width="2"/>`;
		for ( let i = 0; i < N; i ++ ) {
			const u = H.hsn( 5, 6, i, SEED ), x = x0 + u * L;
			s += `<circle cx="${x}" cy="${y}" r="11" fill="${BLUE}"/>`;
			if ( N <= 16 ) s += text( x, y - 24, i, 22, { anchor: 'middle', fill: SUB } );
		}
	} );
	s += text( x0, 320 + 3 * 130 + 62, '0', 23, { fill: SUB, anchor: 'middle' } ) + text( x1, 320 + 3 * 130 + 62, '1', 23, { fill: SUB, anchor: 'middle' } );
	save( 'weyl-time-step', 820, s );
}

// ---- 6. one tile across three frames: same pattern, rotated in value
{
	const cell = 60, y0 = 290, xs = [ 120, 800, 1480 ];
	let s = header( 'A frame step rotates every value by the same amount', [ 'The same 8×8 tile on frames 0, 1 and 2, labelled with the value × 64, rounded down. Each frame adds 0.618 × 64 ≈ 39.6 to every pixel and wraps at 64,', 'so the tile keeps its 64 equally spaced values on every frame while each pixel gets a new one.' ] );
	[ 0, 1, 2 ].forEach( ( f, p ) => {
		s += text( xs[ p ], y0 - 28, `Frame ${f}`, 27, { bold: true } );
		s += cellGrid( xs[ p ], y0, 8, cell, ( i, j ) => { const v = H.hsn( 16 + i, 8 + j, f, SEED ); return { v, label: Math.floor( v * 64 ) }; }, { lines: [ [ 1, 1, '#999' ], [ 8, 5, BLUE ] ] } );
	} );
	save( 'frame-rotation', 830, s );
}

Promise.all( jobs ).then( () => console.log( 'wrote', fs.readdirSync( OUT ).join( ', ' ) ) );
