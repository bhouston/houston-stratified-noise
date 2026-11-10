// Temporal step constants in 0.32 fixed point: step / 2^32 is the fraction added per sample index.
// Each is floor( 2^32 / phi_d^(k+1) ), phi_d the positive root of x^(d+1) = x + 1
// (Martin Roberts' generalized golden ratios). All are odd, so the u32 state has period 2^32.

export const GOLDEN_STEP = 2654435769; // 0x9e3779b9, d = 1 (golden ratio)
export const R2_STEPS = [ 3242174889, 2447445413 ]; // d = 2 (plastic number)
export const R4_STEPS = [ 3679390609, 3152041523, 2700274805, 2313257605 ]; // d = 4
