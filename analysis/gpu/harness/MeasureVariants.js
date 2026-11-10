// Measurement-only sampler variants (not part of any PR). Selected with ?noise=hash|ign|vc|hsnr2|white.
import { Fn, float, interleavedGradientNoise, uint, vec2, vec4 } from 'three/tsl';
import { R2_STEPS, R4_STEPS, bindHierarchicalHashedWeyl, hierarchicalHashedWeyl } from './HierarchicalHashedWeyl.js';
import { bindWhiteNoise } from './MeasureWhiteNoise.js';
import { bindVoidClusterRd } from './MeasureVoidCluster.js';
import { Vector2 } from 'three/webgpu';
import { fastNoise } from './FASTNoise.js'; // verbatim from mrdoob/three.js#35244 (head 98781c8152e5)
import { bindAnalyticNoise as bindAnalyticR4 } from './MeasureRNoiseR4.js'; // verbatim RNoise.js of bhouston/three.js#42, commit 8899ba3e387c
import { R2_ALPHAS, R4_ALPHAS, bindAnalyticPerDimensionLattices, bindAnalyticSingleLattice } from './MeasureAnalyticR4.js';

// --- A. "Hash + R_d": white per-pixel Cranley-Patterson offsets + per-dimension Roberts (R2/R4) Weyl steps.

const pcg = Fn( ( [ input ] ) => {

	const state = uint( input ).mul( uint( 747796405 ) ).add( uint( 2891336453 ) ).toVar();
	const word = state.shiftRight( state.shiftRight( 28 ).add( 4 ) ).bitXor( state ).mul( uint( 277803737 ) ).toVar();
	return word.shiftRight( 22 ).bitXor( word );

} );

export function bindHashRd( resolution, seed = 0, steps = R4_STEPS ) {

	return Fn( ( [ uvCoord, sampleIndex ] ) => {

		const pixel = uvCoord.mul( resolution ).floor();
		const index = uint( sampleIndex ).toConst();
		const state = pcg( uint( pixel.x ).add( pcg( uint( pixel.y ).add( pcg( uint( seed ) ) ) ) ) ).toVar();
		const result = vec4( 0 ).toVar();

		for ( let k = 0; k < steps.length; k ++ ) {

			if ( k > 0 ) state.assign( pcg( state ) ); // next dimension's offset
			result.element( k ).assign( state.add( index.mul( uint( steps[ k ] ) ) ).shiftRight( 8 ).toFloat().div( 16777216 ) );

		}

		return result;

	} );

}

// --- B. "IGN + R_d": interleaved gradient noise phase at a different pixel offset per dimension + per-dimension Roberts Weyl steps.

export function bindIgnRd( resolution, seed = 0, steps = R4_STEPS ) {

	return Fn( ( [ uvCoord, sampleIndex ] ) => {

		const pixel = uvCoord.mul( resolution ).floor().add( 0.5 );
		const index = uint( sampleIndex ).toConst();
		const result = vec4( 0 ).toVar();

		for ( let k = 0; k < steps.length; k ++ ) {

			const offset = vec2( 97 * ( k + 1 ) + 13 * seed, 61 * ( k + 1 ) + 7 * seed );
			const phase = uint( interleavedGradientNoise( pixel.add( offset ) ).mul( 16777216 ) ).shiftLeft( 8 );
			result.element( k ).assign( phase.add( index.mul( uint( steps[ k ] ) ) ).shiftRight( 8 ).toFloat().div( 16777216 ) );

		}

		return result;

	} );

}

// --- C. The pull request noise with the R2 steps (VXGI only): same seeds as bindHierarchicalHashedWeyl( resolution, seed ).xy

export function bindHsnR2( resolution, seed = 0 ) {

	return Fn( ( [ uvCoord, sampleIndex ] ) => {

		const pixel = uvCoord.mul( resolution ).floor();
		return vec4( hierarchicalHashedWeyl( pixel, sampleIndex, seed * 4 + 1, R2_STEPS[ 0 ] ), hierarchicalHashedWeyl( pixel, sampleIndex, seed * 4 + 2, R2_STEPS[ 1 ] ), float( 0 ), float( 0 ) );

	} );

}

// dimensions: 2 for VXGI (R2 steps), 4 for SSR (R4 steps)
export function measureBindNoise( resolution, seed, dimensions ) {

	const steps = dimensions === 2 ? R2_STEPS : R4_STEPS;

	switch ( globalThis.__NOISE ) {

		case 'white': return bindWhiteNoise( resolution, seed );
		case 'hash': return bindHashRd( resolution, seed, steps );
		case 'ign': return bindIgnRd( resolution, seed, steps );
		case 'vc': return bindVoidClusterRd( resolution, seed, steps );
		// e / f: R4 constants (VXGI takes the first two dimensions); er2 / fr2: R2 constants (VXGI only)
		case 'e': return bindAnalyticSingleLattice( resolution, seed, R4_ALPHAS );
		case 'er2': return bindAnalyticSingleLattice( resolution, seed, R2_ALPHAS );
		case 'f': return bindAnalyticPerDimensionLattices( resolution, seed, R4_ALPHAS );
		case 'fr2': return bindAnalyticPerDimensionLattices( resolution, seed, R2_ALPHAS );
		// H: FAST spatio-temporal atlas read with the PR's fastNoise(); the atlas is loaded by measure_common.js before the
		// nodes are built. fastNoise() reads screenCoordinate itself; the seed only picks a fixed integer tile offset.
		case 'h': return Fn( ( [ uvCoord, sampleIndex ] ) => fastNoise( globalThis.__FAST_ATLAS, new Vector2( seed * 13 % 128, seed * 29 % 128 ), uint( sampleIndex ) ) ); // eslint-disable-line no-unused-vars
		case 'g': return bindAnalyticR4( resolution, seed );
		case 'hsnr2': return bindHsnR2( resolution, seed );
		default: return bindHierarchicalHashedWeyl( resolution, seed ); // PR head

	}

}
