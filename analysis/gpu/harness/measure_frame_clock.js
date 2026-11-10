// The measurement pages own their renderer and advance it manually for its whole lifetime.
// Stopping the animation once per frame is insufficient: render()/compute() call start(),
// which immediately increments nodeFrame and schedules more updates between GPU readbacks.
const manualRenderers = new WeakSet();

export function tick( renderer ) {

	if ( ! manualRenderers.has( renderer ) ) {

		if ( renderer._animation._requestId !== null ) renderer._animation.stop();
		renderer._animation.start = () => {}; // prevent render()/compute() from restarting the clock
		manualRenderers.add( renderer );

	}

	renderer._nodes.nodeFrame.update();
	renderer.info.frame = renderer._nodes.nodeFrame.frameId;

}
