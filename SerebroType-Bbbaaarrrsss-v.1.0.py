# MenuTitle: Bbbaaarrrsss
# -*- coding: utf-8 -*-

from GlyphsApp import *
from Foundation import NSPoint
from AppKit import NSBezierPath, NSNonZeroWindingRule
import vanilla, math

PADDING = 12
FIELD_WIDTH = 120
INPUT_WIDTH = 100
WINDOW_WIDTH = PADDING + FIELD_WIDTH + 8 + INPUT_WIDTH + PADDING
WINDOW_HEIGHT = 190

def makeRectPathFromPoints(points):
    p = GSPath()
    p.closed = True
    p.nodes = [GSNode((pt.x, pt.y), LINE) for pt in points]
    return p

def makeRectPath(x0, y0, x1, y1):
    return makeRectPathFromPoints([
        NSPoint(x0, y0),
        NSPoint(x1, y0),
        NSPoint(x1, y1),
        NSPoint(x0, y1),
    ])

def bezierPathFromLayerSafe(layer):
    src = layer.copyDecomposedLayer()
    if not src or not src.shapes or len(src.shapes) == 0:
        return None
    try:
        src.removeOverlap()
    except Exception:
        pass
    bp = getattr(src, "completeBezierPath", None)
    if bp is None:
        bp = getattr(src, "bezierPath", None)
    if bp is not None:
        try:
            bp.setWindingRule_(NSNonZeroWindingRule)
        except Exception:
            pass
        return bp
    return None

def intervalsBySampling(nsbp, y, x_min, x_max, step=0.4, minLen=0.4):
    res = []
    x = x_min
    inside_prev = nsbp.containsPoint_(NSPoint(x, y))
    start = None
    while x <= x_max:
        inside = nsbp.containsPoint_(NSPoint(x, y))
        if inside and not inside_prev:
            start = x
        elif not inside and inside_prev and start is not None:
            if x - start >= minLen:
                res.append((start, x))
            start = None
        inside_prev = inside
        x += step
    if inside_prev and start is not None and x_max - start >= minLen:
        res.append((start, x_max))
    return res

def snapPathsY(paths, targetY, tol=0.5, mode="bottom"):
    for p in paths:
        if not isinstance(p, GSPath):
            continue
        for n in p.nodes:
            if mode == "bottom":
                if n.y < targetY + tol:
                    n.y = targetY
            else:
                if n.y > targetY - tol:
                    n.y = targetY

class BarsUI(object):
    def __init__(self):
        f = Glyphs.font
        if not f or not f.selectedLayers:
            Message("Select a glyph", "Выдели слой глифа и запусти снова.")
            return

        self.w = vanilla.FloatingWindow((WINDOW_WIDTH, WINDOW_HEIGHT), "Bbbaaarrrsss")

        y = PADDING

        self.w.nLbl = vanilla.TextBox((PADDING, y, FIELD_WIDTH, 20), "Bars (count):")
        self.w.n = vanilla.EditText((PADDING + FIELD_WIDTH + 8, y, INPUT_WIDTH, 22), "11")
        y += 28

        self.w.gapLbl = vanilla.TextBox((PADDING, y, FIELD_WIDTH, 20), "Gap:")
        self.w.gap = vanilla.EditText((PADDING + FIELD_WIDTH + 8, y, INPUT_WIDTH, 22), "20")
        y += 28

        self.w.angleLbl = vanilla.TextBox((PADDING, y, FIELD_WIDTH, 20), "Angle (°):")
        self.w.angle = vanilla.EditText((PADDING + FIELD_WIDTH + 8, y, INPUT_WIDTH, 22), "0")
        y += 28

        self.w.fitContour = vanilla.CheckBox(
            (PADDING, y, WINDOW_WIDTH - 2 * PADDING, 20),
            "Fit bars to contour",
            value=False,
            callback=self.toggleContour,
        )
        y += 30

        self.w.go = vanilla.Button(
            (PADDING, y, WINDOW_WIDTH - 2 * PADDING, 28),
            "Build Layer",
            callback=self.build
        )

        self.w.open()

    def toggleContour(self, sender):
        on = bool(sender.get())
        self.w.angle.enable(not on)
        self.w.angleLbl.enable(not on)

    def build(self, sender):
        f = Glyphs.font
        layers = f.selectedLayers

        n   = int(self.w.n.get())
        gap = float(self.w.gap.get())
        fitContour = bool(self.w.fitContour.get())
        angleDeg = float(self.w.angle.get()) if not fitContour else 0.0

        if n < 1:
            Message("Error", "Bars must be ≥ 1")
            return

        sampleStepX = 0.4
        epsilonY = 0.15

        for layer in layers:
            nsbp = bezierPathFromLayerSafe(layer)
            if nsbp is None:
                Message("Error", "В слое нет контуров.")
                return

            bounds = nsbp.bounds()
            yMin = bounds.origin.y
            yMax = bounds.origin.y + bounds.size.height
            totalH = yMax - yMin

            x_min = 0.0
            x_max = layer.width

            neededGaps = (n - 1) * gap
            remainForBars = totalH - neededGaps
            if remainForBars <= 0:
                Message("Error", "Gap слишком большой для этой высоты и количества полос.")
                return
            barH = remainForBars / n

            # Имя слоя
            if fitContour:
                layerName = f"Bars={n}, Gap={gap:g}"
            else:
                if abs(angleDeg) > 0.0001:
                    layerName = f"Bars={n}, Gap={gap:g}, Angle={angleDeg:g}"
                else:
                    layerName = f"Bars={n}, Gap={gap:g}"

            outL = GSLayer()
            outL.name = layerName
            outL.associatedMasterId = layer.associatedMasterId
            outL.width, outL.LSB, outL.RSB = layer.width, layer.LSB, layer.RSB

            if fitContour:
                baseLayer = layer.copyDecomposedLayer()
                baseLayer.removeOverlap()
                srcPaths = list(baseLayer.paths)
                if not srcPaths:
                    Message("Error", "В слое нет контуров (для булева).")
                    return

            y0 = yMin
            for i in range(n):
                yBottom = y0
                if i == n - 1:
                    yTop = yMax
                else:
                    yTop = y0 + barH

                if fitContour:
                    bandBottom = yBottom - (epsilonY if i == 0 else 0)
                    bandTop    = yTop    + (epsilonY if i == n - 1 else 0)
                    band = makeRectPath(x_min, bandBottom, x_max, bandTop)

                    import GlyphsApp
                    clippedPaths = GlyphsApp.intersectPaths(srcPaths, [band])

                    if i == 0:
                        snapPathsY(clippedPaths, yMin, tol=0.6, mode="bottom")
                    if i == n - 1:
                        snapPathsY(clippedPaths, yMax, tol=0.6, mode="top")

                    for cp in clippedPaths:
                        cp.closed = True
                        outL.shapes.append(cp)

                else:
                    yMid = (yBottom + yTop) * 0.5
                    intervals = intervalsBySampling(nsbp, yMid, x_min, x_max, step=sampleStepX)

                    ang = math.radians(angleDeg)
                    dx = math.tan(ang) * (yTop - yBottom) if angleDeg != 0 else 0.0

                    for (xx0, xx1) in intervals:
                        if angleDeg == 0:
                            outL.shapes.append(
                                makeRectPath(xx0, yBottom, xx1, yTop)
                            )
                        else:
                            pts = [
                                NSPoint(xx0, yBottom),
                                NSPoint(xx1, yBottom),
                                NSPoint(xx1 + dx, yTop),
                                NSPoint(xx0 + dx, yTop),
                            ]
                            outL.shapes.append(makeRectPathFromPoints(pts))

                y0 += barH
                if i < n - 1:
                    y0 += gap

            outL.removeOverlap()
            layer.parent.layers.append(outL)

BarsUI()