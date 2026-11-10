// Interactive explorer: runs the src/noise modules on the CPU into 2D canvases.
import { S, el } from './common.js';
import { NOISES, GOLDEN_STEP, R4_STEPS, TRADEOFF_R4_STEPS, stepsFor, historyWeight } from '../../src/noise/index.js';

const N = 256, PAD = 32, M = N + 2 * PAD; // 256x256 view plus a margin so the blur (truncated at 4 sigma, sigma <= 8) never sees an edge
const ORIGIN = 1024 - PAD; // the view starts at the tile-aligned screen coordinate (1024, 1024)
const PIXEL = ( PAD + 21 ) * M + PAD + 13; // the pixel whose samples the scatter view plots
const noises = NOISES.map( ( n ) => ( { ...n, label: n.label.replaceAll( 'HSN', S ) + ( n.animated ? '' : ' (static)' ) } ) );

// Test functions f(u) with their exact means, by number of values per pixel (a subset of analysis/temporal/integrands.py).
const INTEGRANDS = {
	1: [
		[ 'Noise value u', ( u ) => u[ 0 ], () => 0.5 ],
		[ 'Thresholded, u < t', ( u, t ) => u[ 0 ] < t ? 1 : 0, ( t ) => t ]
	],
	2: [
		[ 'u < v (diagonal edge)', ( u ) => u[ 0 ] < u[ 1 ] ? 1 : 0, () => 0.5 ],
		[ 'u + v < 1 (anti-diagonal edge)', ( u ) => u[ 0 ] + u[ 1 ] < 1 ? 1 : 0, () => 0.5 ],
		[ 'Disc, radius 0.4', ( u ) => ( u[ 0 ] - 0.5 ) ** 2 + ( u[ 1 ] - 0.5 ) ** 2 < 0.16 ? 1 : 0, () => Math.PI * 0.16 ],
		[ 'Box, u < 0.3 and v < 0.6', ( u ) => u[ 0 ] < 0.3 && u[ 1 ] < 0.6 ? 1 : 0, () => 0.18 ],
		[ 'Product u·v', ( u ) => u[ 0 ] * u[ 1 ], () => 0.25 ]
	],
	4: [
		[ 'u1 < u3 and u2 < u4', ( u ) => u[ 0 ] < u[ 2 ] && u[ 1 ] < u[ 3 ] ? 1 : 0, () => 0.25 ],
		[ 'u1 < u3 (one pair)', ( u ) => u[ 0 ] < u[ 2 ] ? 1 : 0, () => 0.5 ],
		[ 'u1 + u2 + u3 + u4 < 2', ( u ) => u[ 0 ] + u[ 1 ] + u[ 2 ] + u[ 3 ] < 2 ? 1 : 0, () => 0.5 ],
		[ 'Mean of the four values', ( u ) => ( u[ 0 ] + u[ 1 ] + u[ 2 ] + u[ 3 ] ) / 4, () => 0.5 ],
		[ 'Product u1·u2·u3·u4', ( u ) => u[ 0 ] * u[ 1 ] * u[ 2 ] * u[ 3 ], () => 1 / 16 ]
	]
};

const STEPS = [
	[ 'Default: golden / R2 / R4, one step per value', ( D ) => stepsFor( D ) ],
	[ 'Shared golden step for every value (lockstep failure)', ( D ) => Array( D ).fill( GOLDEN_STEP ) ],
	[ 'First values of R4 (as Three.js VXGI uses for two)', ( D ) => R4_STEPS.slice( 0, D ) ],
	[ 'Trade-off candidate from the step search (four values; not the default)', ( D ) => TRADEOFF_R4_STEPS.slice( 0, D ) ]
];

const $ = ( id ) => document.getElementById( id );
const options = ( list ) => list.map( ( [ name ], i ) => `<option value="${i}">${name}</option>` ).join( '' );
$( 'steps' ).innerHTML = options( STEPS );

// the noise and test-function menus depend on the number of values per pixel
function menus() {

	const D = + $( 'values' ).value;
	const list = noises.filter( ( n ) => D === 1 || n.multi ).map( ( n ) => `<option value="${n.id}">${n.label}</option>` ).join( '' );

	for ( const [ id, none, fallback ] of [ [ 'a', '', 'hsn' ], [ 'b', '<option value="">None</option>', 'hash-rd' ] ] ) {

		const previous = $( id ).value;
		$( id ).innerHTML = none + list;
		$( id ).value = previous;
		if ( $( id ).selectedIndex < 0 ) $( id ).value = fallback;

	}

	$( 'integrand' ).innerHTML = options( INTEGRANDS[ D ] );
	$( 'threshold' ).disabled = D !== 1;

}

menus();
$( 'a' ).value = 'hsn';
$( 'b' ).value = 'ign-animated';
$( 'values' ).addEventListener( 'input', menus );

const settings = () => {

	const D = + $( 'values' ).value, [ name, f, mean ] = INTEGRANDS[ D ][ + $( 'integrand' ).value ], threshold = + $( 'threshold' ).value;
	return {
		D, f, target: mean( threshold ), integrand: name, steps: STEPS[ + $( 'steps' ).value ][ 1 ]( D ),
		seed: + $( 'seed' ).value, threshold, sigma: + $( 'sigma' ).value,
		mode: $( 'mode' ).value, alpha: + $( 'alpha' ).value, frame: + $( 'frame' ).value, gain: + $( 'gain' ).value
	};

};

// ---- panels

const VIEWS = [ [ 'pattern', 'Current frame (first value)' ], [ 'second', '' ], [ 'spectrum', 'Log power spectrum' ], [ 'result', 'Blurred accumulation: error × gain' ] ];
const STATS = [ [ 'mean', 'Mean of the frame (first value)' ], [ 'raw', 'RMS error, one frame, no filter' ], [ 'accumulated', 'RMS error, accumulated, no blur' ], [ 'filtered', 'RMS error, accumulated and blurred' ], [ 'tiles', 'Aligned 8×8 tiles exactly stratified' ], [ 'frames', 'Frames accumulated' ] ];

function makePanel( slot ) {

	const root = el( `<section class="panel" data-slot="${slot}"><h3></h3>
		<div class="views">${VIEWS.map( ( [ id, name ] ) => `<figure><canvas width="${N}" height="${N}" data-view="${id}" role="img" aria-label="${name}"></canvas><figcaption>${name}</figcaption></figure>` ).join( '' )}</div>
		<dl class="stats">${STATS.map( ( [ id, name ] ) => `<dt>${name}</dt><dd data-stat="${id}"></dd>` ).join( '' )}</dl></section>` );
	$( 'panels' ).append( root );
	const ctx = Object.fromEntries( VIEWS.map( ( [ id ] ) => [ id, root.querySelector( `[data-view=${id}]` ).getContext( '2d' ) ] ) );
	return { root, ctx, image: new ImageData( N, N ), key: '', done: - 1, cur: new Float32Array( M * M ), acc: new Float32Array( M * M ), points: [] };

}

const panels = [ makePanel( 'a' ), makePanel( 'b' ) ];

// Advance a panel's accumulation by one frame. Returns false when it has reached the target frame.
function step( panel, noise, s ) {

	const target = noise.animated ? s.frame : 0; // a static noise is the same every frame, so one frame is its accumulation
	const key = [ noise.id, s.seed, s.D, s.integrand, s.D === 1 ? s.threshold : '', s.steps, s.mode, s.mode === 'ema' ? s.alpha : '' ].join();
	if ( key !== panel.key || panel.done > target ) { panel.key = key; panel.done = - 1; panel.points = []; }
	if ( panel.done === target ) return false;

	const index = ++ panel.done, { cur, acc } = panel, { D, f, steps, seed, threshold } = s, fn = noise.fn, u = [ 0, 0, 0, 0 ];
	const weight = historyWeight( index + 1, s.alpha ); // history ramp-up: running mean for the first 1 / alpha frames, then EMA

	for ( let j = 0, k = 0; j < M; j ++ ) for ( let i = 0; i < M; i ++, k ++ ) {

		for ( let d = 0; d < D; d ++ ) u[ d ] = fn( ORIGIN + i, ORIGIN + j, index, seed, d, steps );
		cur[ k ] = u[ 0 ];
		if ( k === PIXEL ) panel.points.push( [ u[ 0 ], u[ 1 ] ] );
		const g = f( u, threshold );
		if ( index === 0 ) acc[ k ] = g;
		else if ( s.mode === 'ema' ) acc[ k ] += weight * ( g - acc[ k ] );
		else acc[ k ] += g; // running sum; divided by the frame count when read

	}

	return panel.done < target;

}

// ---- image processing

const tmp = new Float32Array( M * M ), blurred = new Float32Array( N * N );

// Separable Gaussian truncated at 4 sigma, evaluated only for the central N x N.
function blur( src, scale, sigma ) {

	const radius = Math.min( PAD, Math.ceil( 4 * sigma ) ), w = [];
	for ( let d = - radius; d <= radius; d ++ ) w.push( sigma > 0 ? Math.exp( - d * d / ( 2 * sigma * sigma ) ) : 1 );
	const sum = w.reduce( ( a, b ) => a + b );

	for ( let j = PAD - radius; j < PAD + N + radius; j ++ ) for ( let i = PAD; i < PAD + N; i ++ ) {

		let v = 0;
		for ( let d = - radius; d <= radius; d ++ ) v += w[ d + radius ] * src[ j * M + i + d ];
		tmp[ j * M + i ] = v / sum;

	}

	for ( let j = 0; j < N; j ++ ) for ( let i = 0; i < N; i ++ ) {

		let v = 0;
		for ( let d = - radius; d <= radius; d ++ ) v += w[ d + radius ] * tmp[ ( j + PAD + d ) * M + i + PAD ];
		blurred[ j * N + i ] = v / sum * scale;

	}

	return blurred;

}

// In-place radix-2 FFT of length N (a power of two).
const re = new Float64Array( N * N ), im = new Float64Array( N * N ), rowRe = new Float64Array( N ), rowIm = new Float64Array( N );
const cos = Float64Array.from( { length: N / 2 }, ( _, k ) => Math.cos( 2 * Math.PI * k / N ) ), sin = Float64Array.from( { length: N / 2 }, ( _, k ) => - Math.sin( 2 * Math.PI * k / N ) );

function fft( a, b ) {

	for ( let i = 1, j = 0; i < N; i ++ ) {

		let bit = N >> 1;
		for ( ; j & bit; bit >>= 1 ) j ^= bit;
		j ^= bit;
		if ( i < j ) { let t = a[ i ]; a[ i ] = a[ j ]; a[ j ] = t; t = b[ i ]; b[ i ] = b[ j ]; b[ j ] = t; }

	}

	for ( let size = 2; size <= N; size <<= 1 ) for ( let start = 0, half = size >> 1, stride = N / size; start < N; start += size ) for ( let k = 0; k < half; k ++ ) {

		const p = start + k, q = p + half, c = cos[ k * stride ], s = sin[ k * stride ];
		const tr = a[ q ] * c - b[ q ] * s, ti = a[ q ] * s + b[ q ] * c;
		a[ q ] = a[ p ] - tr; b[ q ] = b[ p ] - ti; a[ p ] += tr; b[ p ] += ti;

	}

}

// Power spectrum of the central N x N of a field, DC removed, normalised so uniform white noise averages 1 per bin.
function spectrum( field ) {

	let mean = 0;
	for ( let j = 0; j < N; j ++ ) for ( let i = 0; i < N; i ++ ) mean += field[ ( j + PAD ) * M + i + PAD ];
	mean /= N * N;
	for ( let j = 0; j < N; j ++ ) for ( let i = 0; i < N; i ++ ) { re[ j * N + i ] = field[ ( j + PAD ) * M + i + PAD ] - mean; im[ j * N + i ] = 0; }

	for ( let j = 0; j < N; j ++ ) { const a = re.subarray( j * N, j * N + N ), b = im.subarray( j * N, j * N + N ); fft( a, b ); }

	for ( let i = 0; i < N; i ++ ) {

		for ( let j = 0; j < N; j ++ ) { rowRe[ j ] = re[ j * N + i ]; rowIm[ j ] = im[ j * N + i ]; }
		fft( rowRe, rowIm );
		for ( let j = 0; j < N; j ++ ) re[ j * N + i ] = ( rowRe[ j ] ** 2 + rowIm[ j ] ** 2 ) / ( N * N / 12 );

	}

	return re; // power, unshifted

}

const INFERNO = [ [ 0, 0, 4 ], [ 87, 16, 110 ], [ 188, 55, 84 ], [ 249, 142, 9 ], [ 252, 255, 164 ] ];

function draw( panel, view, pixel ) {

	const d = panel.image.data;

	for ( let k = 0; k < N * N; k ++ ) {

		const c = pixel( k % N, ( k / N ) | 0 );
		if ( typeof c === 'number' ) { d[ 4 * k ] = d[ 4 * k + 1 ] = d[ 4 * k + 2 ] = c * 255; } else { d[ 4 * k ] = c[ 0 ]; d[ 4 * k + 1 ] = c[ 1 ]; d[ 4 * k + 2 ] = c[ 2 ]; }
		d[ 4 * k + 3 ] = 255;

	}

	panel.ctx[ view ].putImageData( panel.image, 0, 0 );

}

function render( panel, noise, s ) {

	const { cur, acc } = panel, at = ( i, j ) => ( j + PAD ) * M + i + PAD;
	const frames = panel.done + 1, scale = s.mode === 'mean' ? 1 / frames : 1, target = s.target;

	draw( panel, 'pattern', ( i, j ) => cur[ at( i, j ) ] );

	if ( s.D === 1 ) {

		draw( panel, 'second', ( i, j ) => cur[ at( i, j ) ] < s.threshold ? 0 : 1 );

	} else { // one pixel's (first, second) values on every accumulated frame

		const c = panel.ctx.second;
		c.fillStyle = '#fff'; c.fillRect( 0, 0, N, N );
		c.fillStyle = '#2f6fd0';
		for ( const [ u, v ] of panel.points ) c.fillRect( u * N - 1.5, ( 1 - v ) * N - 1.5, 3, 3 );

	}

	panel.root.querySelector( '[data-view=second] + figcaption' ).textContent = s.D === 1 ? 'Thresholded at t' : 'One pixel\'s (first, second) values, every frame so far';

	const p = spectrum( cur );
	draw( panel, 'spectrum', ( i, j ) => {

		const v = Math.log10( Math.max( p[ ( ( j + N / 2 ) % N ) * N + ( i + N / 2 ) % N ], 1e-9 ) ); // fftshift
		const u = Math.min( Math.max( ( v + 3 ) / 4.5, 0 ), 0.9999 ) * 4, a = INFERNO[ u | 0 ], b = INFERNO[ ( u | 0 ) + 1 ], f = u - ( u | 0 );
		return [ a[ 0 ] + ( b[ 0 ] - a[ 0 ] ) * f, a[ 1 ] + ( b[ 1 ] - a[ 1 ] ) * f, a[ 2 ] + ( b[ 2 ] - a[ 2 ] ) * f ];

	} );

	const result = blur( acc, scale, s.sigma );
	draw( panel, 'result', ( i, j ) => Math.min( Math.max( 0.5 + ( result[ j * N + i ] - target ) * s.gain, 0 ), 1 ) );

	let mean = 0, accumulated = 0, filtered = 0, tiles = 0;

	for ( let j = 0; j < N; j ++ ) for ( let i = 0; i < N; i ++ ) {

		mean += cur[ at( i, j ) ]; accumulated += ( acc[ at( i, j ) ] * scale - target ) ** 2; filtered += ( result[ j * N + i ] - target ) ** 2;

	}

	for ( let ty = 0; ty < N; ty += 8 ) for ( let tx = 0; tx < N; tx += 8 ) {

		let seen = 0n;
		for ( let j = 0; j < 8; j ++ ) for ( let i = 0; i < 8; i ++ ) seen |= 1n << BigInt( Math.floor( cur[ at( tx + i, ty + j ) ] * 64 ) );
		if ( seen === 0xffffffffffffffffn ) tiles ++;

	}

	if ( frames === 1 ) panel.raw = Math.sqrt( accumulated / ( N * N ) ); // the first frame's unfiltered error
	const stat = { mean: ( mean / ( N * N ) ).toFixed( 4 ), raw: panel.raw.toFixed( 4 ), accumulated: Math.sqrt( accumulated / ( N * N ) ).toFixed( 5 ), filtered: Math.sqrt( filtered / ( N * N ) ).toFixed( 5 ), tiles: `${tiles} / ${( N / 8 ) ** 2}`, frames: noise.animated ? frames : '1 (static)' };
	for ( const id in stat ) panel.root.querySelector( `[data-stat=${id}]` ).textContent = stat[ id ];

}

// ---- main loop: accumulate in slices of about 12 ms per animation frame so the controls stay responsive

let scheduled = false, playing = false;

function tick() {

	scheduled = false;
	const s = settings();
	for ( const id of [ 'seed', 'threshold', 'sigma', 'alpha', 'frame' ] ) $( `${id}-value` ).textContent = s[ id ];
	let busy = false;

	panels.forEach( ( panel, k ) => {

		const noise = noises.find( ( n ) => n.id === $( k ? 'b' : 'a' ).value );
		panel.root.hidden = ! noise;
		if ( ! noise ) return;
		panel.root.querySelector( 'h3' ).textContent = noise.label;
		const end = performance.now() + 12;
		let more = step( panel, noise, s );
		if ( panel.done === 0 ) render( panel, noise, s ); // records the single-frame error
		while ( more && performance.now() < end ) more = step( panel, noise, s );
		busy ||= more;
		render( panel, noise, s );

	} );

	if ( ! busy && playing ) {

		if ( s.frame < + $( 'frame' ).max ) { $( 'frame' ).value = s.frame + 1; busy = true; } else { playing = false; $( 'play' ).textContent = 'Play'; }

	}

	if ( busy ) schedule();

}

function schedule() {

	if ( ! scheduled ) { scheduled = true; requestAnimationFrame( tick ); }

}

$( 'controls' ).addEventListener( 'input', schedule );
$( 'play' ).addEventListener( 'click', () => {

	playing = ! playing;
	$( 'play' ).textContent = playing ? 'Pause' : 'Play';
	if ( playing && + $( 'frame' ).value === + $( 'frame' ).max ) $( 'frame' ).value = 0;
	schedule();

} );

schedule();
