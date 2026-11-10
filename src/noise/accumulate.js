// Temporal accumulation with a TAA-style history ramp-up.

// Blend weight of the new frame when it is the n-th frame since the history was reset (n = 1 for the first):
// a running mean while the history is shorter than the EMA's 1 / alpha frames, then the usual EMA.
export const historyWeight = ( n, alpha ) => Math.max( 1 / n, alpha );

// history after blending in `value` as the n-th frame. For n <= 1 / alpha this is exactly the arithmetic
// mean of the first n values, so no frame (and no initial value) is over-weighted.
export const accumulate = ( history, value, n, alpha ) => history + historyWeight( n, alpha ) * ( value - history );
