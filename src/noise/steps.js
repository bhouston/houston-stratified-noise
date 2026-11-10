// Temporal step constants in 0.32 fixed point: step / 2^32 is the fraction added per sample index.
// Each is floor( 2^32 / phi_d^(k+1) ), phi_d the positive root of x^(d+1) = x + 1
// (Martin Roberts' generalized golden ratios). All are odd, so the u32 state has period 2^32.

export const GOLDEN_STEP = 2654435769; // 0x9e3779b9, d = 1 (golden ratio)
export const R2_STEPS = [ 3242174889, 2447445413 ]; // d = 2 (plastic number)
export const R4_STEPS = [ 3679390609, 3152041523, 2700274805, 2313257605 ]; // d = 4

// The default steps for 1, 2 or 4 values per pixel.
export const stepsFor = ( dimensions ) => ( { 1: [ GOLDEN_STEP ], 2: R2_STEPS, 4: R4_STEPS } )[ dimensions ];

// OPTIONAL, NOT THE DEFAULT. The four-value candidate from the step search (analysis/steps). It did not pass
// the search's acceptance rule: against R4_STEPS it is much better per pixel from 16 frames on and under
// EMA + blur on held-out integrands, but 1-9% worse for 4- and 8-frame windows with a blur. Use all four
// together; its first two steps are a poor two-value pair.
export const TRADEOFF_R4_STEPS = [ 3280154747, 2481977421, 1303403687, 2746543331 ];

// The same R_d constants as float fractions, for the float-time baselines.
const PHI = ( 1 + Math.sqrt( 5 ) ) / 2, PLASTIC = 1.32471795724474602596, PHI4 = 1.1673039782614187;
export const RD_ALPHAS = { 1: [ 1 / PHI ], 2: [ 1 / PLASTIC, 1 / PLASTIC ** 2 ], 4: [ 1, 2, 3, 4 ].map( ( k ) => 1 / PHI4 ** k ) };
