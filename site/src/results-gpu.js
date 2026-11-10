// In-engine section of the Results page, rendered from results/gpu (measured on real GPU hardware).
import { S, command, dataTable, figure, list, r } from './common.js';
import { rt, realtime, bakeTable, sensitivityTable, FAST } from './data.js';
import g from './gpu-readings.json';

const a = rt.vxgi.adapter;
const GPU = command( 'pnpm analysis:gpu' ) + '<p class="cmd">This regenerates the figures from the committed metrics and image crops. The measurements themselves need the harness and a hardware WebGPU adapter: see <code>analysis/gpu/README.md</code>.</p>';

document.getElementById( 'engine-body' ).innerHTML = `
	<p>Measurements of the Three.js pull request in the engine: its head against its merge base for real-time VXGI and denoised SSR, and a light map bake, plus four simpler fixes run through the same harness. The published numbers were measured on a hardware WebGPU adapter (vendor <code>${a.vendor}</code>, architecture <code>${a.architecture}</code>, not a fallback adapter: an Apple M3) in ${rt.vxgi.chrome.replace( '/', ' ' )}.</p>
	${GPU}
	<h3>Lead finding: level with the FAST blue-noise textures, at zero bytes</h3>
	<p>In SSR and VXGI under TRAA, ${S} is level with the FAST blue-noise textures on frame RMSE (VXGI 9.99 against 10.18, within run-to-run variation; SSR 2.982 against 2.981), at zero bytes against a 3.0 MB atlas. The error is distributed differently: in VXGI FAST has 19% lower bias while ${S} has 7% less temporal noise and 4% less flicker; in SSR ${S} has 15% lower bias while FAST has about 1% less noise and flicker. The plain hash with per-value steps also matches or beats FAST on RMSE. The flat-field gaps against FAST did not carry over to the engine, likely because TRAA and the denoiser are not the filter the FAST atlas is optimised for (untested). Scope: two effects, a static camera, one GPU, and FAST call sites written for this measurement.</p>
	<p class="caption">VXGI, real time (two values per pixel). H is the FAST spatio-temporal atlas of mrdoob/three.js#35244, sampled with that pull request's own <code>FASTNoise.js</code>.</p>
	${realtime( 'vxgi', 2, 3, FAST )}
	<p class="caption">SSR, denoised (four values per pixel).</p>
	${realtime( 'ssr', 3, 3, FAST )}
	<p>${r( g.h_fps )}</p>
	${dataTable( { head: g.h_table[ 0 ].map( r ), rows: g.h_table.slice( 1 ).map( ( row ) => row.map( r ) ) } )}
	${list( g.h_plain )}
	<p><strong>How H uses the FAST textures:</strong></p>
	${list( g.h_uses )}
	<p><strong>Agreement with the CPU flat-field result:</strong> mostly not, in size; partly, in sign.</p>
	${list( g.h_agreement )}
	<p>${r( g.h_caveat )}</p>

	${figure( 'gpu/figures/in-engine-results.webp', 'Measured change against the previous code for VXGI, SSR and the light map bake' )}

	<h3>Before and after: VXGI, real time</h3>
	<p class="caption">${r( g.tables_note )} Signal RMS ${rt.vxgi.rms_signal.toFixed( 4 )}.</p>
	${realtime( 'vxgi', 2, 3 )}

	<h3>Before and after: SSR, denoised</h3>
	<p class="caption">Signal RMS ${rt.ssr.rms_signal.toFixed( 4 )}.</p>
	${realtime( 'ssr', 3 )}
	<p>${r( g.fps_note )}</p>
	<p class="caption">${r( g.ssr_only_note )}</p>
	${realtime( 'ssr_only', 3 )}
	${list( g.verdict )}

	<h3>Before and after: light map bake, 64 samples</h3>
	${bakeTable}
	${list( g.bake_findings )}
	<p class="caption">How much grainier the shared step is depends on how grain is defined:</p>
	${sensitivityTable}
	${list( g.bake_sensitivity )}

	<h3>Against simpler fixes</h3>
	<p>${r( g.simpler_intro )}</p>
	${figure( 'gpu/figures/in-engine-variants.webp', 'Frame crops and amplified error for every sampler variant' )}
	${dataTable( { head: g.simpler_table[ 0 ].map( r ), rows: g.simpler_table.slice( 1 ).map( ( row ) => row.map( r ) ) } )}
	${list( g.simpler_plain )}
	<p><strong>Like for like on VXGI.</strong> The shipped ${S} row uses the first two R4 steps, while A, B and D use R2 steps. Comparing equal step sets (variant C, ${S} with R2 steps, against variant A), the hash is about 4% lower on RMSE (8.86 against 9.26) with about 24% more flicker (5.07 against 4.09). The 13% and 18% figures above compare the shipped configuration with the hash and so mix the two step sets. Frame rate: no measurable change between the samplers is claimed; the GPU was shared.</p>
	<p>${r( g.simpler_caveat )}</p>

	<h3>Exact TSL for A (hash + R_d) and B (IGN + R_d)</h3>
	<pre><code>${g.tsl.replace( /&/g, '&amp;' ).replace( /</g, '&lt;' )}</code></pre>
	<p>${r( g.callsites )} These in-engine variants chain the PCG hash differently from <code>hashRd</code> and <code>ignRd</code> in <code>src/noise/rd.js</code>, which follow the CPU temporal analysis; both are a per-pixel phase plus the same per-dimension steps.</p>
	<p><strong>Variant D (void-and-cluster + R_d) as measured:</strong></p>
	${list( g.variant_d )}

	<h3>Method</h3>
	${list( g.setup )}
	${list( g.method )}
	${list( g.bake_method )}

	<h3>Limits</h3>
	${list( g.limits )}
`;
