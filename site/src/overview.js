import { S, figure, table } from './common.js';
import spatial from '../../results/spatial/tables.json';
import readings from './spatial-readings.json';

for ( const slot of document.querySelectorAll( '[data-figure]' ) ) slot.outerHTML = figure( slot.dataset.figure, slot.dataset.alt );

document.getElementById( 'headline' ).textContent = readings.headline.replaceAll( '{S}', S );

// the eleven main methods of three headline tables, straight from the committed results
document.getElementById( 'key-tables' ).innerHTML = [ 'E1', 'F1', 'D2' ].map( ( id ) => {

	const t = spatial.tables.find( ( t ) => t.id === id );
	return `<h3>${t.title.replace( /^\w+\. /, '' )}</h3>${table( t, 11 )}`;

} ).join( '' );
