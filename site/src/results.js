import { S, command, figure, md, table } from './common.js';
import spatial from '../../results/spatial/tables.json';
import structure from '../../results/solution/structure.json';
import pairs from '../../results/solution/step-pairs.json';
import readings from './spatial-readings.json';

const r = ( text ) => md( text.replaceAll( '{S}', S ) );
const list = ( items, tag = 'ul' ) => `<${tag}>${items.map( ( i ) => `<li>${r( i )}</li>` ).join( '' )}</${tag}>`;

// ---- structure (analysis/solution)

const SOLUTION = command( 'pnpm analysis:solution' );
const f = ( v, d ) => v.toFixed( d );

const windows = {
	head: [ 'Offset', 'Distinct bins occupied', 'Window-mean RMS error', 'White: bins occupied', 'White: RMS error' ],
	rows: structure.windows.map( ( w ) => [ `${w.size}×${w.size}`, `(${w.offset})`, `${f( w.occupied, 2 )} / ${w.bins}`, f( w.rms, 4 ), `${f( w.whiteOccupied, 2 )} / ${w.bins}`, f( w.whiteRms, 4 ) ] )
};

const columns = Object.keys( structure.discrepancy[ 0 ] ).filter( ( k ) => k !== 'N' );
const discrepancy = {
	head: structure.discrepancy.map( ( d ) => `N=${d.N}` ),
	rows: columns.map( ( c ) => [ c === 'white' ? 'White noise' : c, ...structure.discrepancy.map( ( d ) => f( d[ c ], 4 ) ) ] )
};

const stepPairs = {
	head: [ 'N=64', 'N=256', 'N=1024', 'Strongest near-relation p·α₀ + q·α₁ ≈ integer (p, q)', 'Distance from integer' ],
	rows: pairs.map( ( p ) => [ p.steps, f( p.l2star[ 64 ], 4 ), f( p.l2star[ 256 ], 4 ), f( p.l2star[ 1024 ], 4 ), `${p.resonance.p}, ${p.resonance.q}`, p.resonance.error.toExponential( 2 ) ] )
};

const dims = structure.dimensions;
const dimensions = {
	head: [ 'Quadrant-count RMS deviation (ideal 16 each)', '4×4 grid deviation', '8×8 grid cells occupied (of 64)' ],
	rows: [ [ S, dims.hsn ], [ 'Random Latin-hypercube pairing', dims.lhs ], [ 'White noise', dims.white ] ].map( ( [ name, d ] ) => [ name, f( d.dev2, 2 ), f( d.dev4, 2 ), f( d.occ8, 2 ) ] )
};

document.getElementById( 'structure-body' ).innerHTML = `
	<p>Checks of what the construction guarantees, run on the plain-JavaScript reference. The full printed output is <code>results/solution/structure.txt</code>; the algorithm diagrams on the <a href="./">Overview</a> page come from the same command.</p>
	${SOLUTION}

	<h3>Aligned and unaligned windows</h3>
	${table( windows ).replace( '<th>Method</th>', '<th>Window</th>' )}
	<p>Guarantees hold only for windows aligned to the 2, 4 and 8 pixel grid. A 2×2 window shifted diagonally by one pixel is statistically white. Larger unaligned windows degrade gracefully because they still contain whole aligned sub-blocks: an 8×8 window at any offset tested has a mean 1.8 to 8 times more accurate than white noise. A 4×4 window at offset (4,4) is aligned again.</p>

	<h3>Two dimensions within a tile</h3>
	${table( dimensions ).replace( '<th>Method</th>', '<th>64 (u,v) pairs per aligned tile</th>' )}
	<p>Using two seeds over 4,096 tiles, each tile's 64 (u,v) pairs have perfect 1D marginals in both dimensions, but their joint 2D distribution is no better than white noise. Dimensions are independent, not jointly stratified; the joint quality of multi-dimensional samples comes from the temporal steps, not from space.</p>

	<h3>Per-pixel 2D point sets over time, by step pair</h3>
	<p>L2 star discrepancy of one pixel's first N two-dimensional samples (lower is better), mean over pixels.</p>
	${table( discrepancy ).replace( '<th>Method</th>', '<th>Steps</th>' )}
	${table( stepPairs ).replace( '<th>Method</th>', '<th>Steps</th>' )}
	<p>A step shared by both dimensions stalls at about 0.075 and never converges. <code>R4_STEPS[0]</code> and <code>[2]</code> nearly satisfy α₀ + 5·α₂ = 4.000208, so that pair sits close to a small family of lines and barely improves between 256 and 1,024 samples. Whether these differences are visible in rendering was not tested here.</p>
`;

// ---- spatial (analysis/spatial)

const SPATIAL = command( 'pnpm analysis:spatial' );
const reading = ( start ) => readings.reading.flatMap( ( g ) => g.items ).find( ( i ) => i.startsWith( `**${start}` ) );

const figures = [
	[ 'swatches', 'One frame of each noise' ], [ 'swatches-threshold', 'The same crops thresholded at 50%' ], [ 'spectra-2d', 'Power spectra' ],
	[ 'radial-power', 'Radially averaged power spectrum' ], [ 'anisotropy', 'Radial anisotropy' ], [ 'filtered-error', 'Error left after a Gaussian blur' ],
	[ 'threshold-error-by-level', 'Filtered threshold error by threshold level' ], [ 'window-stratification', 'Local stratification: error of window means' ],
	[ 'window-offsets', `${S}: what happens off the 8×8 grid` ], [ 'autocorrelation', 'Autocorrelation at small lags' ], [ 'histograms', 'Value histograms' ]
];

// which bullets of "Reading the numbers" speak to which table
const tableReadings = {
	A: [ 'Uniform histogram' ], D1: [ 'Depth of the low-frequency hole', 'No blue-noise peak or plateau' ], D2: [ 'Isotropy', 'No spectral peaks' ],
	E1: [ 'Filtered value error' ], E2: [ 'Filtered threshold error' ], E4: [ 'Wide-filter threshold error' ],
	F1: [ 'Stratification is tied to the grid' ], F2: [ 'No 8-pixel spectral lines' ], G: [ 'Nearest neighbours are anti-correlated', 'Anti-correlation exists only inside 2×2 blocks' ]
};

document.getElementById( 'spatial-body' ).innerHTML = `
	<p>${r( readings.headline )}</p>
	<p>Scope: one frame (sample index 0), one scalar per pixel. Nothing in this section says anything about temporal convergence or multi-dimensional sampling.</p>
	${SPATIAL}

	<h3>Methods as implemented</h3>
	<p>${r( readings.protocol )}</p>
	${table( { head: [ 'Definition', 'Arithmetic', 'Realizations' ], rows: readings.methods.map( ( row ) => row.map( r ) ) } )}
	${list( readings.definitions )}

	${figures.map( ( [ name, title ] ) => `<h3 id="${name}">${title}</h3>${figure( `spatial/figures/${name}.webp`, title, readings.figures[ name ].replaceAll( '{S}', S ) )}` ).join( '' )}

	${spatial.tables.map( ( t ) => `<h3 id="table-${t.id}">${t.title}</h3>${table( t )}${( tableReadings[ t.id ] || [] ).map( ( start ) => `<p>${r( reading( start ) )}</p>` ).join( '' )}` ).join( '' )}

	<h3>${S} details</h3>
	${list( spatial.details )}

	${readings.reading.slice( 2 ).map( ( g ) => `<h3>${r( g.title )}</h3>${list( g.items )}` ).join( '' )}

	<h3>Surprises</h3>
	${list( readings.surprises, 'ol' )}

	<h3>Caveats and limits</h3>
	${list( readings.caveats )}

	<h3>Gaps worth follow-on work</h3>
	${list( readings.gaps )}
`;
