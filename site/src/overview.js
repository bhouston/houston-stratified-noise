import { S, dataTable, figure, table } from './common.js';
import { headline, realtime } from './data.js';
import spatial from '../../results/spatial/tables.json';
import readings from './spatial-readings.json';
import ablation from '../../results/r4-ablation/tables_ABL.json';

for ( const slot of document.querySelectorAll( '[data-figure]' ) ) slot.outerHTML = figure( slot.dataset.figure, slot.dataset.alt );

// headline tables, straight from the committed results
document.getElementById( 'accumulated-table' ).innerHTML = dataTable( headline );
document.getElementById( 'vxgi-table' ).innerHTML = realtime( 'vxgi', 2, 3 );
document.getElementById( 'ssr-table' ).innerHTML = realtime( 'ssr', 3 );

document.getElementById( 'ablation-table' ).innerHTML = dataTable( ablation[ 0 ], { caption: false } );

document.getElementById( 'headline' ).textContent = readings.headline.replaceAll( '{S}', S );

// the eleven main methods of three single-frame tables
document.getElementById( 'key-tables' ).innerHTML = [ 'E1', 'F1', 'D2' ].map( ( id ) => {

	const t = spatial.tables.find( ( t ) => t.id === id );
	return `<h4>${t.title.replace( /^\w+\. /, '' )}</h4>${table( t, 11 )}`;

} ).join( '' );
