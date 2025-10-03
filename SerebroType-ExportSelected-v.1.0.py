# MenuTitle: Export selected instanses
# Description:
# Select specific instances from the active font and export as Source (.glyphs), TTF, or OTF.
# Version: 1.0 (Master)
# Author: Denis Serebryakov
# Requirements: Glyphs 3+, Vanilla

# -*- coding: utf-8 -*-
from __future__ import annotations

import os, time, re, traceback
import GlyphsApp
from GlyphsApp import Glyphs, GSFont
import vanilla
from AppKit import (
    NSOnState, NSOffState, NSMixedState, NSOpenPanel, NSImageRight
)

# ---------- helpers ----------
def sanitize_filename(name: str) -> str:
    for bad in r'\/:*?"<>|':
        name = name.replace(bad, "-")
    return name.strip()

def ensure_dir(path: str):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def export_instance(font, instance, dest_folder, fmt,
                    remove_overlap=True, autohint=True, production_names=True) -> str:
    fmt = fmt.upper()
    if fmt not in {"TTF", "OTF"}:
        raise ValueError("Unsupported format: %s" % fmt)

    family_raw = font.familyName or "Untitled"
    base_name = re.sub(r"\s*\(.*?\)", "", family_raw).strip()
    style = instance.name or instance.styleName or "Regular"
    stem = f"{base_name}-{style}".replace(" ", "")
    ext = fmt.lower()

    ensure_dir(dest_folder)
    full_path = os.path.join(dest_folder, f"{stem}.{ext}")
    t0 = time.time()

    flags = dict(
        AutoHint=bool(autohint),
        RemoveOverlap=bool(remove_overlap),
        UseProductionNames=bool(production_names),
    )

    candidates = [
        dict(format=fmt, FontPath=full_path, **flags),
        dict(Format=fmt, FontPath=full_path, **flags),
        dict(format=fmt, path=full_path, **flags),
        dict(Format=fmt, path=full_path, **flags),
        dict(format=fmt, FontPath=dest_folder, **flags),
        dict(Format=fmt, FontPath=dest_folder, **flags),
        dict(format=fmt, path=dest_folder, **flags),
        dict(Format=fmt, path=dest_folder, **flags),
    ]

    last_err = None
    for kw in candidates:
        try:
            instance.generate(font, **kw)
            if os.path.exists(full_path):
                return full_path
            fresh = [os.path.join(dest_folder, fn)
                     for fn in os.listdir(dest_folder)
                     if fn.lower().endswith("." + ext)
                     and os.path.getmtime(os.path.join(dest_folder, fn)) >= t0]
            if fresh:
                fresh.sort(key=os.path.getmtime, reverse=True)
                src = fresh[0]
                if src != full_path:
                    try: os.replace(src, full_path)
                    except Exception: return src
                return full_path
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Export failed for {fmt}. Last error: {last_err}")

def generate_source_glyphs(font, instance, dest_folder) -> str:
    interp = instance.interpolatedFont
    if not isinstance(interp, GSFont):
        raise RuntimeError("interpolatedFont failed")
    fam = font.familyName or "Untitled"
    sty = instance.name or instance.styleName or "Regular"
    interp.familyName = fam
    if interp.masters and len(interp.masters) == 1:
        interp.masters[0].name = sty
    fn = f"{sanitize_filename(fam)}-{sanitize_filename(sty)}.glyphs"
    path = os.path.join(dest_folder, fn)
    interp.save(path)
    return path

# ---------- UI ----------
class ExportSelectedUI:
    BASE_MIN_W = 520
    BASE_MAX_W = 900
    MIN_W_SMALL = 360
    AVG_CHAR_W = 7
    ROW_H = 22
    PAD = 14
    LIST_INSET = 10
    MAX_ROWS_NO_SCROLL = 10
    GAP_SCROLL_TO_TYPES   = 16
    GAP_TYPES_TO_OPTIONS  = 16
    GAP_OPTIONS_TO_BTNS   = 16
    BOTTOM_PAD = 16
    ALL_Y_NUDGE = -2  # подстройка по линии заголовка

    def __init__(self):
        try:
            self.font = Glyphs.font
            if not self.font:
                Glyphs.showMacroWindow()
                print("⚠️ Откройте шрифт (File → Open).")
                return

            fam = self.font.familyName or "Untitled"
            titles = [f"{fam} {(inst.name or inst.styleName or 'Regular')}" for inst in self.font.instances]
            max_len = max([len(t) for t in titles], default=24)

            base_w = max(self.BASE_MIN_W, min(self.BASE_MAX_W, 120 + int(self.AVG_CHAR_W * max_len)))
            w = max(self.MIN_W_SMALL, int(base_w * 0.5))

            n = max(1, len(titles))
            visible_rows = min(n, self.MAX_ROWS_NO_SCROLL)
            scroll_h = self.LIST_INSET*2 + visible_rows * self.ROW_H

            title_h   = 20
            types_h   = 20 + 3*24
            options_h = 20 + 3*24
            btn_h     = 28

            h = (self.PAD + title_h + 6 + scroll_h +
                 self.GAP_SCROLL_TO_TYPES + types_h +
                 self.GAP_TYPES_TO_OPTIONS + options_h +
                 self.GAP_OPTIONS_TO_BTNS + btn_h + self.BOTTOM_PAD)

            self.w = vanilla.FloatingWindow((w, h), "Export selected instanses")

            # Заголовок
            self.w.titleLabel = vanilla.TextBox((self.PAD, self.PAD, -self.PAD, 20), "Select instanses:")

            # Список инстансов
            scrollTop   = self.PAD + 20 + 6
            scrollWidth = w - 2*self.PAD
            self._scrollWidth = scrollWidth
            self.doc, self._cb_by_index, self._inst_indices = self.buildInstanceGroup(scrollWidth, n)
            self.w.scroll = vanilla.ScrollView((self.PAD, scrollTop, scrollWidth, scroll_h),
                                               self.doc.getNSView())
            try:
                self.w.scroll.getNSScrollView().setHasHorizontalScroller_(False)
            except Exception:
                pass

            # Чекбокс ALL с лейблом-счётчиком, прижат вправо
            total = len(self._cb_by_index)
            all_title = f"0 from {total}"
            self.w.cbAll = vanilla.CheckBox((0, self.PAD + self.ALL_Y_NUDGE, 60, 20),
                                            all_title, value=False, callback=self.onToggleAll)
            try:
                ns = self.w.cbAll._nsObject
                ns.setAllowsMixedState_(True)
                ns.setImagePosition_(NSImageRight)  # текст слева (наш счётчик), чекбокс справа
                ns.sizeToFit()
                all_w = int(ns.fittingSize().width)
            except Exception:
                all_w = 60
            right_edge = self.PAD + scrollWidth
            all_x = right_edge - all_w
            self.w.cbAll.setPosSize((all_x, self.PAD + self.ALL_Y_NUDGE, all_w, 20))

            # Select export types
            typesTop = scrollTop + scroll_h + self.GAP_SCROLL_TO_TYPES
            x = self.PAD
            self.w.typesLabel = vanilla.TextBox((x, typesTop, 200, 20), "Export types:")
            ty = typesTop + 22
            self.w.cbSource = vanilla.CheckBox((x, ty,         200, 20), "Source file (.glyphs)", value=True,  callback=self.onTypesChanged)
            self.w.cbTTF    = vanilla.CheckBox((x, ty + 24,    100, 20), "TTF",                   value=False, callback=self.onTypesChanged)
            self.w.cbOTF    = vanilla.CheckBox((x, ty + 48,    100, 20), "OTF",                   value=False, callback=self.onTypesChanged)

            # Options
            optsTop = ty + 48 + 20 + self.GAP_TYPES_TO_OPTIONS
            self.w.optsLabel = vanilla.TextBox((x, optsTop, 200, 20), "Options:")
            oy = optsTop + 22
            self.w.cbRO = vanilla.CheckBox((x, oy,          180, 20), "Remove Overlap",  value=True)
            self.w.cbAH = vanilla.CheckBox((x, oy + 24,     180, 20), "Autohint",        value=True)
            self.w.cbPN = vanilla.CheckBox((x, oy + 48,     220, 20), "Production Names", value=True)

            # Кнопки: Cancel + Export
            btn_h = 28
            cancel_w = 100
            gap_wanted = 16
            gap_min    = 8
            export_min = 120
            export_pref = 240

            inner_w = w - 2 * self.PAD
            export_w = min(export_pref, max(export_min, inner_w - cancel_w - gap_wanted))
            gap_now  = max(gap_min, min(gap_wanted, inner_w - cancel_w - export_w))

            cancel_x = self.PAD
            export_x = cancel_x + cancel_w + gap_now

            self.w.btnCancel = vanilla.Button(
                (cancel_x, -self.BOTTOM_PAD - btn_h, cancel_w, btn_h),
                "Cancel",
                callback=lambda s: self.w.close(),
            )
            self.w.btnExport = vanilla.Button(
                (export_x, -self.BOTTOM_PAD - btn_h, export_w, btn_h),
                "Export",
                callback=self.onExport,
            )

            self._lastFolder = os.path.expanduser("~/Desktop/Exports")

            # стартовое состояние
            self.updateAllCheckboxState()
            self.updateOptionsEnabled()
            self.updateExportEnabled()  # экспорт неактивен при пустом выборе типов/инстансов

            self.w.open()

        except Exception as e:
            Glyphs.showMacroWindow()
            print("✖ Ошибка UI:", e)
            print(traceback.format_exc())

    def buildInstanceGroup(self, scroll_width: int, n_instances: int):
        fam = self.font.familyName or "Untitled"
        instances = list(self.font.instances)

        doc_w = scroll_width
        totalH = self.LIST_INSET + n_instances*self.ROW_H + self.LIST_INSET
        grp = vanilla.Group((0, 0, doc_w, totalH))

        cb_list, index_map = [], []
        y = self.LIST_INSET
        cb_width = doc_w - 2*self.LIST_INSET
        for idx, inst in enumerate(instances):
            style = inst.name or inst.styleName or "Regular"
            title = f"{fam} {style}"
            cb = vanilla.CheckBox(
                (self.LIST_INSET, y, cb_width, 20), title, value=False,
                callback=self.onInstanceCheck
            )
            setattr(grp, f"cb_{idx}", cb)
            cb_list.append(cb)
            index_map.append(idx)
            y += self.ROW_H

        return grp, cb_list, index_map

    # ----- selection helpers -----
    def selectedInstances(self):
        out = []
        all_instances = list(self.font.instances)
        for i, cb in enumerate(self._cb_by_index):
            if cb.get():
                inst_index = self._inst_indices[i]
                if 0 <= inst_index < len(all_instances):
                    out.append(all_instances[inst_index])
        return out

    # --- NEW: состояние кнопки Export (учитывает и типы, и выбранные инстансы)
    def exportTypesSelected(self) -> bool:
        return bool(self.w.cbSource.get() or self.w.cbTTF.get() or self.w.cbOTF.get())

    def anyInstancesSelected(self) -> bool:
        return any(cb.get() for cb in self._cb_by_index)

    def updateExportEnabled(self):
        try:
            self.w.btnExport.enable(self.exportTypesSelected() and self.anyInstancesSelected())
        except Exception:
            pass

    def _repositionCbAll(self):
        try:
            ns = self.w.cbAll._nsObject
            ns.sizeToFit()
            all_w = int(ns.fittingSize().width)
        except Exception:
            all_w = 60
        right_edge = self.PAD + self._scrollWidth
        all_x = right_edge - all_w
        self.w.cbAll.setPosSize((all_x, self.PAD + self.ALL_Y_NUDGE, all_w, 20))

    def updateCountInCbAll(self):
        count = sum(1 for cb in self._cb_by_index if cb.get())
        total = len(self._cb_by_index)
        try:
            self.w.cbAll._nsObject.setTitle_(f"{count} from {total}")
        except Exception:
            self.w.cbAll.setTitle(f"{count} from {total}")
        self._repositionCbAll()

    def updateAllCheckboxState(self):
        total = len(self._cb_by_index)
        checked = sum(1 for cb in self._cb_by_index if cb.get())
        ns = self.w.cbAll._nsObject
        if checked == 0:
            ns.setState_(NSOffState)
        elif checked == total:
            ns.setState_(NSOnState)
        else:
            try: ns.setAllowsMixedState_(True)
            except Exception: pass
            ns.setState_(NSMixedState)
        self.updateCountInCbAll()
        self.updateExportEnabled()  # <-- обновляем доступность Export при любом изменении выбора инстансов

    def updateOptionsEnabled(self):
        enabled = bool(self.w.cbTTF.get() or self.w.cbOTF.get())
        for ctl in (self.w.cbRO, self.w.cbAH, self.w.cbPN):
            try: ctl.enable(enabled)
            except Exception: pass

    # колбэки
    def onTypesChanged(self, sender):
        self.updateOptionsEnabled()
        self.updateExportEnabled()  # следим за кнопкой Export при изменении типов

    def onInstanceCheck(self, sender):
        self.updateAllCheckboxState()

    def onToggleAll(self, sender):
        total = len(self._cb_by_index)
        checked = sum(1 for cb in self._cb_by_index if cb.get())
        make_all_on = checked != total
        for cb in self._cb_by_index:
            cb.set(bool(make_all_on))
        self.updateAllCheckboxState()

    def chooseFolder(self, title="Select destination folder"):
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(False)
        panel.setCanChooseDirectories_(True)
        panel.setCanCreateDirectories_(True)
        panel.setAllowsMultipleSelection_(False)
        panel.setMessage_(title)
        if panel.runModal() == 1:
            url = panel.URL()
            if url:
                folder = url.path()
                ensure_dir(folder)
                self._lastFolder = folder
                return folder
        return None

    # ----- actions -----
    def onExport(self, sender):
        targets = self.selectedInstances()
        if not targets:
            Glyphs.showNotification("Export Selected", "Nothing selected.")
            return

        do_source = bool(self.w.cbSource.get())
        fmts = []
        if self.w.cbTTF.get():  fmts.append("TTF")
        if self.w.cbOTF.get():  fmts.append("OTF")

        if not (do_source or fmts):
            Glyphs.showNotification("Export Selected", "Choose export types.")
            return

        remove_overlap    = bool(self.w.cbRO.get()) if fmts else False
        autohint          = bool(self.w.cbAH.get()) if fmts else False
        production_names  = bool(self.w.cbPN.get()) if fmts else False

        dest = self.chooseFolder("Select destination folder")
        if not dest: return

        ok_src = ok_bin = fail = 0

        if do_source:
            for inst in targets:
                try:
                    generate_source_glyphs(self.font, inst, dest)
                    ok_src += 1
                except Exception:
                    fail += 1

        for inst in targets:
            for fmt in fmts:
                try:
                    export_instance(self.font, inst, dest, fmt,
                                    remove_overlap=remove_overlap,
                                    autohint=autohint,
                                    production_names=production_names)
                    ok_bin += 1
                except Exception:
                    fail += 1

        Glyphs.showNotification("Export Selected",
                                f"Sources {ok_src}, Fonts {ok_bin}, Failed {fail}")

# run
ExportSelectedUI()
