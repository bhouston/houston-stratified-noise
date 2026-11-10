import test from 'node:test';
import assert from 'node:assert/strict';
import { tick } from './measure_frame_clock.js';

// Models Three.js Animation.start(): an immediate frame advance plus a queued RAF.
// render() calls start() even for an otherwise on-demand renderer.
function createRenderer() {

	let nextId = 0, stops = 0;
	const callbacks = new Map();
	const nodeFrame = { frameId: 0, update() { this.frameId ++; } };
	const animation = {
		_requestId: null,
		start() {

			if ( this._requestId !== null ) return;
			const update = () => {

				this._requestId = ++ nextId;
				callbacks.set( this._requestId, update );
				nodeFrame.update();

			};
			update();

		},
		stop() {

			stops ++;
			callbacks.delete( this._requestId );
			this._requestId = null;

		}
	};
	return {
		_animation: animation,
		_nodes: { nodeFrame },
		info: { frame: 0 },
		render() { animation.start(); return nodeFrame.frameId; },
		flushBackgroundUpdates() {

			for ( const [ id, callback ] of [ ...callbacks ] ) {

				callbacks.delete( id );
				callback();

			}

		},
		get pendingUpdates() { return callbacks.size; },
		get stops() { return stops; }
	};

}

test( 'manual frames survive nested render calls and asynchronous readbacks without index drift', async () => {

	const renderer = createRenderer();
	const indices = [];
	for ( let frame = 0; frame < 8; frame ++ ) {

		tick( renderer );
		indices.push( renderer.render() );
		assert.equal( renderer.render(), frame + 1, 'nested passes share one frame index' );
		await Promise.resolve(); // readback yields to background work
		renderer.flushBackgroundUpdates();
		assert.equal( renderer._nodes.nodeFrame.frameId, frame + 1 );
		assert.equal( renderer.info.frame, frame + 1 );
		assert.equal( renderer.pendingUpdates, 0 );

	}
	assert.deepEqual( indices, [ 1, 2, 3, 4, 5, 6, 7, 8 ] );

} );

test( 'taking over an already running clock cancels its pending update', () => {

	const renderer = createRenderer();
	renderer.render();
	assert.equal( renderer._nodes.nodeFrame.frameId, 1 );
	assert.equal( renderer.pendingUpdates, 1 );
	tick( renderer );
	assert.equal( renderer.stops, 1 );
	renderer.render();
	renderer.flushBackgroundUpdates();
	assert.equal( renderer._nodes.nodeFrame.frameId, 2 );
	assert.equal( renderer.pendingUpdates, 0 );
	tick( renderer );
	assert.equal( renderer.stops, 1, 'taking ownership is idempotent' );
	assert.equal( renderer.info.frame, 3 );

} );

test( 'each measurement renderer has its own manual frame clock', () => {

	const a = createRenderer(), b = createRenderer();
	tick( a );
	b.render();
	b.flushBackgroundUpdates();
	assert.equal( a._nodes.nodeFrame.frameId, 1 );
	assert.equal( b._nodes.nodeFrame.frameId, 2 );
	tick( b );
	assert.equal( a._nodes.nodeFrame.frameId, 1 );
	assert.equal( b._nodes.nodeFrame.frameId, 3 );
	assert.equal( b.pendingUpdates, 0 );

} );
