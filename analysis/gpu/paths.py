"""Shared locations for the in-engine measurement scripts.

RAW   the harness output (per-run JSON and float32 images, about 1.1 GB): analysis/gpu/raw, or $GPU_RAW. Not committed.
OUT   results/gpu: the committed metrics JSON, per-run JSON (runs/) and figures.
CROPS analysis/gpu/crops: the small 8-bit image crops the figures show, committed so the figures can be regenerated.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RAW = os.environ.get('GPU_RAW', os.path.join(HERE, 'raw')) + '/'
OUT = os.path.join(ROOT, 'results/gpu') + '/'
CROPS = os.path.join(HERE, 'crops') + '/'
NAMES = json.load(open(os.path.join(ROOT, 'names.json')))


def named(text):
    """Figure labels are written with the default name; the display name comes from names.json."""
    return text.replace('Houston Stratified Noise', NAMES['name']).replace('HSN', NAMES['short'])


def savefig(fig, name):
    import io
    import matplotlib.text
    from PIL import Image
    for t in fig.findobj(matplotlib.text.Text):
        t.set_text(named(t.get_text()))
    png = io.BytesIO()
    fig.savefig(png, dpi=100, format='png')
    os.makedirs(OUT + 'figures', exist_ok=True)
    Image.open(png).convert('RGB').save(OUT + f'figures/{name}.webp', quality=92, method=6)
