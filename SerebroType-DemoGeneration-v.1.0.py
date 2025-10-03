#MenuTitle: Demo version generation
# -*- coding: utf-8 -*-
# Description:
# Quickly prepare a demo version of the font with suffix, minimal glyph set, optional traps, and .notdef control.
# Version: 1.0 (Master)
# Author: Denis Serebryakov
# Requirements: Glyphs 3+, Vanilla

import GlyphsApp
from GlyphsApp import GSPath, GSNode, LINE
import vanilla
import re
from AppKit import NSFont

# FUNCTION
def remove_features(trialFont):
    trialFont.features = []
    
def remove_featurePrefixes(trialFont):
    trialFont.featurePrefixes = []
    
def remove_classes(trialFont):
    trialFont.classes = []

def replace_with_component(font, source_name, target_name):
    source_glyph = font.glyphs[source_name]
    target_glyph = font.glyphs[target_name]

    if source_glyph and target_glyph:
        for master in font.masters:
            target_layer = target_glyph.layers[master.id]
            target_layer.shapes = []
            component = GSComponent(source_name)
            target_layer.shapes.append(component)
            source_layer = source_glyph.layers[master.id]
            target_layer.width = source_layer.width
            target_layer.leftMetricsKey = None
            target_layer.rightMetricsKey = None

def swap_glyph_content(font, source_name, target_name):
    source_glyph = font.glyphs[source_name]
    target_glyph = font.glyphs[target_name]
    
    if not source_glyph or not target_glyph:
        return

    for master in font.masters:
        source_layer = source_glyph.layers[master.id]
        target_layer = target_glyph.layers[master.id]
        source_layer.shapes = [shape.copy() for shape in target_layer.shapes]
        source_layer.width = target_layer.width

def create_empty_notdef(font):
    notdef = GSGlyph(".notdef")
    notdef.category = "Letter"
    notdef.subCategory = "Other"
    font.glyphs.append(notdef)

    for master in font.masters:
        layer = font.glyphs[".notdef"].layers[master.id]
        layer.clear()
        
        original_height = 700
        original_width = 612
        scale = master.capHeight / original_height
        layer.width = int(original_width * scale)

        shapes = [
            [(50, 0), (562, 0), (562, 700), (50, 700)],
            [(100, 604), (275, 350), (100, 95)],
            [(306, 305), (481, 50), (131, 50)],
            [(481, 649), (306, 394), (131, 649)],
            [(512, 604), (512, 95), (337, 350)],
        ]

        for shape in shapes:
            path = GSPath()
            path.closed = True
            for x, y in shape:
                node = GSNode((x * scale, y * scale), type=GSLINE)
                path.nodes.append(node)
            layer.paths.append(path)

        layer.correctPathDirection()

def insert_predefined_notdef(font):
    if not font.glyphs[".notdef"]:
        create_empty_notdef(font)

    for master in font.masters:
        layer = font.glyphs[".notdef"].layers[master.id]
        layer.clear()
        
        original_height = 700
        original_width = 612
        scale = master.capHeight / original_height
        layer.width = int(original_width * scale)

# DEMO MARK
        shapes = [
            [(50, 0), (562, 0), (562, 700), (50, 700)],
            [(83, 450), (162, 450), (186, 403), (186, 298), (162, 251), (83, 251)],
            [(143, 291), (143, 410), (126, 410), (126, 291)],
            [(203, 450), (279, 450), (279, 411), (246, 411), (246, 372), (279, 372),
             (279, 333), (246, 333), (246, 290), (279, 290), (279, 251), (203, 251)],
            [(296, 450), (329, 450), (353, 403), (377, 450), (410, 450), (410, 251),
             (368, 251), (368, 345), (337, 345), (337, 251), (296, 251)],
            [(427, 290), (427, 411), (446, 450), (510, 450), (530, 411), (530, 290),
             (510, 251), (446, 251)],
            [(487, 291), (487, 410), (470, 410), (470, 291)]
        ]

        for shape in shapes:
            path = GSPath()
            path.closed = True
            for x, y in shape:
                node = GSNode((x * scale, y * scale), type=GSLINE)
                path.nodes.append(node)
            layer.paths.append(path)

        layer.correctPathDirection()

# MAIN FUNCTION
def make_trial_font(selected_prefix="Demo", apply_trial_trap=False, notdef_mode=0, open_in_glyphs=True):
    font = Glyphs.font
    if not font:
        Glyphs.showNotification("Demo version generation", "Error! Open the source file before running the script.")
        return

# PREFIX WORD
    trial_suffix_text = selected_prefix

# COPY FONT
    trialFont = font.copy()

# RENAME FONT
    base_name = re.sub(r'\s*\(.*?\)', '', font.familyName).strip()
    trialFont.familyName = f"{base_name} ({trial_suffix_text})"

# APP LICENSE PARAMETER
    trialFont.customParameters["License"] = f"{trial_suffix_text} version for evaluation purposes only. Not for commercial use."

# INSERT .NOTDEF
    if notdef_mode == 0:
        if not trialFont.glyphs['.notdef']:
            create_empty_notdef(trialFont)
    elif notdef_mode == 1:
        insert_predefined_notdef(trialFont)

# VALIDATION TRIAL TRAP CHECKBOX 
    if apply_trial_trap:
        # Decompose helpers
        for name in ["i", "j", "Iishort-cy", "iishort-cy", "Io-cy", "io-cy", "Oslash", "oslash"]:
            g = trialFont.glyphs[name]
            if g:
                for layer in g.layers:
                    if layer.shapes and layer.components:
                        layer.decomposeComponents()

# CHANGE GLYPHS
        swap_glyph_content(trialFont, "O", "Oslash")
        swap_glyph_content(trialFont, "o", "oslash")
# CHANGE CYRILLIC
        replace_with_component(trialFont, "Ie-cy", "Io-cy")        
        replace_with_component(trialFont, "ie-cy", "io-cy")        
        replace_with_component(trialFont, "Ii-cy", "Iishort-cy")   
        replace_with_component(trialFont, "ii-cy", "iishort-cy")   
        replace_with_component(trialFont, "Sha-cy", "Shcha-cy")    
        replace_with_component(trialFont, "sha-cy", "shcha-cy")    

# DECOMPOSE GLYPHS
    for name in ["i", "j", "Oslash", "oslash", "Iishort-cy", "iishort-cy", "Io-cy", "io-cy"]:
        g = trialFont.glyphs[name]
        if g:
            for layer in g.layers:
                if layer.shapes and layer.components:
                    layer.decomposeComponents()
                    
# REMOVE HELPER GLYPHS AFTER DECOMPOSE
    helpers = ["dotlessi", "dotaccentcomb", "brevecomb-cy.case", "brevecomb-cy", "dieresiscomb", "dieresiscomb.case"]
    for name in helpers:
        g = trialFont.glyphs[name]
        if g:
            trialFont.removeGlyph_(g)

# BUILD ALLOWED GLYPHS LIST
    basic_unicode_list = list(range(0x0041, 0x005A + 1)) + list(range(0x0061, 0x007A + 1))  # A-Z, a-z
    basic_unicode_list += list(range(0x0410, 0x042F + 1)) + list(range(0x0430, 0x044F + 1))  # А-Я, а-я
    basic_unicode_list += list(range(0x0030, 0x0039 + 1))  # 0–9
    basic_unicode_list += [0x002E, 0x002C, 0x002D]  # period, comma, hyphen

    glyphs_to_keep = set()
    for glyph in trialFont.glyphs:
        if glyph.unicode:
            try:
                if int(glyph.unicode, 16) in basic_unicode_list:
                    glyphs_to_keep.add(glyph.name)
            except Exception:
                pass

# ADD REQUIRED GLYPHS
    glyphs_to_keep.update(["i", "j", "Iishort-cy", "iishort-cy", "Io-cy", "io-cy", ".notdef"])
    
# REMOVE ALL OTHER GLYPHS NOT IN KEEP LIST
    for glyph in trialFont.glyphs[:]:
        if glyph.name not in glyphs_to_keep:
            trialFont.removeGlyph_(glyph)

# CLEAN UP GSClasses
    for gsClass in trialFont.classes[:]:
        if gsClass.code:
            glyphNames = gsClass.code.split()
            updatedGlyphNames = [name for name in glyphNames if trialFont.glyphs[name] is not None]
            if updatedGlyphNames:
                gsClass.code = " ".join(updatedGlyphNames)
            else:
                trialFont.classes.remove(gsClass)

# CLEAN OTF AND OTHER
    remove_features(trialFont)
    remove_featurePrefixes(trialFont)
    remove_classes(trialFont)

# OPEN NEW FILE
    if open_in_glyphs:
        Glyphs.fonts.append(trialFont)
    
    return trialFont

# UI
class TrialMasterUI(object):
    def __init__(self):
        margin = 20  
        line_height = 22  
        block_spacing = 20  
        block_internal_spacing = 0  
        button_height = 30   
        create_button_width = 140

        window_width = 300
        window_height = 310 

        self.window = vanilla.FloatingWindow(
            (window_width, window_height),
            "Demo version generation",
        )

        y = margin

# FRAME INNER MARGINS
        inner_top = 4
        text_height = 20
        box_height = 44

# FRAME WITH FONT NAME
        self.window.nameBox = vanilla.Box(
            (margin, y, -margin, box_height)
        )

        font = Glyphs.font
        font_name = font.familyName if font and font.familyName else "Font Name"
        base_font_name = re.sub(r'\s*\(.*?\)', '', font_name).strip()

        self.window.nameBox.titleLabel = vanilla.TextBox(
            (10, inner_top, -10, text_height),
            f"{base_font_name} (Demo)",
            alignment="center"
        )

# FONT SIZE
        self.window.nameBox.titleLabel.getNSTextField().setFont_(
            NSFont.systemFontOfSize_(18)
        )

# MARGIN AFTER
        y += box_height + block_spacing

# .NOTDEF: TITLE
        self.window.notdefTitle = vanilla.TextBox((margin, y, -margin, line_height), "Select .notdef:")
        y += line_height + block_internal_spacing

# .NOTDEF: RADIO GROUP
        current_margin = margin
        self.notdefTitles = ["Default (create if missing)", "Special ‘Demo’ mark"]
        self.window.notdefRadio = vanilla.RadioGroup(
            (current_margin, y, -margin, line_height * 2),
            self.notdefTitles,
            isVertical=True,
        )
        self.window.notdefRadio.set(0)
        y += line_height * 2 + block_spacing

# TRIAL TRAP: TITLE
        self.window.trialTrapTitle = vanilla.TextBox((margin, y, -margin, line_height), "Demo Trap:")
        y += line_height + block_internal_spacing

# TRIAL TRAP: CHECKBOX 
        current_margin = margin
        self.window.trialTrap = vanilla.CheckBox(
            (current_margin, y, -margin, line_height),
            "Swap O/o→Ø/ø, Й/й→И/и, etc.",
            value=False,
        )
        y += line_height + 5

# BUTTON POSITION
        button_y = window_height - margin - button_height
        center_x = (window_width - create_button_width) // 2
        
        y += block_spacing

# BUTTON SOURCE
        self.window.createButton = vanilla.Button(
            (margin, 230, -margin, button_height),
            "Build Source File",
            callback=self.runScript,
        )

        self.window.open()

        y += button_height + 6
        
# BUTTON EXPORT        
        self.window.exportButton = vanilla.Button(
            (margin, 260, -margin, button_height),
             "Export TTF's",
            callback=self.exportDemoFonts
        )
        
    def runScript(self, sender):
        notdef_mode = self.window.notdefRadio.get()
        apply_trial_trap = self.window.trialTrap.get()

        trial_suffix_text = "Demo"

        make_trial_font(
            selected_prefix=trial_suffix_text,
            apply_trial_trap=apply_trial_trap,
            notdef_mode=notdef_mode,
            open_in_glyphs=True 
        )
        
        Glyphs.showNotification("Demo version generation", "Success! Source file is ready.")
        self.window.close()
        
    def exportDemoFonts(self, sender):
        import os

        trialFont = make_trial_font(
            selected_prefix="Demo",
            apply_trial_trap=self.window.trialTrap.get(),
            notdef_mode=self.window.notdefRadio.get(),
            open_in_glyphs=False
        )

        base_font_name = re.sub(r'\s*\(.*?\)', '', trialFont.familyName or "Untitled").strip()

        export_folder_name = f"{base_font_name} (Demo).ttf"

        export_dir = os.path.join(os.path.expanduser("~/Desktop"), export_folder_name)
        os.makedirs(export_dir, exist_ok=True)
        
        for instance in trialFont.instances:
            if instance.active:
                filename = f"{base_font_name} (Demo)-{instance.name}.ttf".replace(" ", "")
                full_path = os.path.join(export_dir, filename)

            try:
                instance.generate(FontPath=full_path, format="TTF")
                print(f"✅Exported {filename}")
            except Exception as e:
                print(f"❌Failed to export {filename}: {e}")

        Message("Demo files exported. Folder created on Desktop.", "Export Succes")
        self.window.close()
        
    def closeWindow(self, sender):
        self.window.close()

# LAUNCH IU
TrialMasterUI()