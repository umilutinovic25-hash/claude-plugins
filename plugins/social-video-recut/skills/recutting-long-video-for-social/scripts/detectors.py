"""Frame detectors on source.mp4 (1920x1080 assumed; coordinates scale with frame size)."""
import cv2, numpy as np

FPS = None
_cap = None

def _frame(t):
    global _cap, FPS
    if _cap is None:
        _cap = cv2.VideoCapture("source.mp4")
        FPS = _cap.get(cv2.CAP_PROP_FPS)
    _cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * FPS))
    ok, img = _cap.read()
    return img if ok else None

def source_caption(t):
    """Creator's burned-in caption: centred, fixed baseline near bottom, white/yellow text with dark outline.
    Returns bbox (x0,y0,x1,y1) in source px or None."""
    img = _frame(t)
    if img is None:
        return None
    H, W = img.shape[:2]; k = W / 1920
    y0, y1, x0, x1 = int(900 * k), int(1070 * k), int(300 * k), int(1620 * k)
    band = img[y0:y1, x0:x1].astype(np.int16)
    bright = (band.min(axis=2) > 215) | ((band[:, :, 2] > 200) & (band[:, :, 1] > 170) & (band[:, :, 0] < 100))
    dark = cv2.dilate((band.max(axis=2) < 45).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    ys, xs = np.nonzero(bright & dark)
    if len(xs) < 800 * k * k:
        return None
    bb = (int(xs.min()) + x0, int(ys.min()) + y0, int(xs.max()) + x0, int(ys.max()) + y0)
    reg = img[bb[1]:bb[3] + 1, bb[0]:bb[2] + 1]
    fill = float((reg.min(axis=2) > 215).mean()) if reg.size else 0
    # badges/lower-thirds are filled boxes (fill>0.6) or off-centre; captions sit on a fixed baseline
    if abs((bb[0] + bb[2]) / 2 - W / 2) > 160 * k or not (1012 * k <= bb[3] <= 1045 * k) or fill > 0.6 or bb[2] - bb[0] > 1450 * k or bb[3] - bb[1] < 30 * k:
        return None
    return bb

def timer_graphic(t):
    """Big countdown timer (dark rounded box, white or fire-orange digits) bottom-left."""
    img = _frame(t)
    if img is None:
        return False
    H, W = img.shape[:2]; k = W / 1920
    reg = img[int(840 * k):int(1060 * k), int(20 * k):int(520 * k)]
    b, g, r = (reg[:, :, i].astype(int) for i in range(3))
    dark = (reg.max(axis=2) < 30).mean()
    white = (reg.min(axis=2) > 225).mean()
    orange = ((r > 200) & (g > 110) & (g < 235) & (b < 120)).mean()
    return bool(dark > 0.25 and (white > 0.12 or orange > 0.03))
