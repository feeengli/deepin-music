#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011~2012 Deepin, Inc.
#               2011~2012 Hou Shaohui
#
# Author:     Hou Shaohui <houshao55@gmail.com>
# Maintainer: Hou ShaoHui <houshao55@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gtk
import cairo
import pango
import pangocairo
import math
from widget.ui import app_theme
import copy
import gobject
from config import config
from render_lyrics import render_lyrics
from utils import color_hex_to_cairo
from dtk.ui.window import Window

# drag state.
DRAG_NONE = 1
DRAG_MOVE = 2
DRAG_EAST = 3
DRAG_WEST = 4
MIN_WIDTH = 300

COLORS_MAP = {
    "inactive" : [
        color_hex_to_cairo(config.get("lyrics", "inactive_color_upper")),
        color_hex_to_cairo(config.get("lyrics", "inactive_color_middle")),
        color_hex_to_cairo(config.get("lyrics", "inactive_color_bottom")),
                  ],
    "active" : [
        color_hex_to_cairo(config.get("lyrics", "active_color_upper")),
        color_hex_to_cairo(config.get("lyrics", "active_color_middle")),
        color_hex_to_cairo(config.get("lyrics", "active_color_bottom")),
        ]
    }

class LyricsWindow(gobject.GObject):
    __gsignals__ = {
        "moved" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "resized" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "hide-bg" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "show-bg" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        }
    def __init__(self):
        super(LyricsWindow, self).__init__()
        
        self.lyrics_win = gtk.Window(gtk.WINDOW_POPUP)
        self.lyrics_win.set_property("allow-shrink", True)
        self.lyrics_win.set_skip_taskbar_hint(True)
        self.lyrics_win.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)
        # self.lyrics_win.set_position(gtk.WIN_POS_CENTER)
        self.lyrics_win.set_decorated(False)
        self.lyrics_win.set_app_paintable(True)
        self.lyrics_win.set_keep_above(True)
        self.lyrics_win.set_colormap(gtk.gdk.Screen().get_rgba_colormap())
        
        self.render_lyrics = render_lyrics
        self.render_lyrics.connect("font-changed", self.update_font)
        self.bg_pixbuf = app_theme.get_pixbuf("skin/desktop_lrc.png").get_pixbuf()
        self.line_padding = 0.0
        self.is_composited  = self.lyrics_win.is_composited()
        self.dock_drag_state = DRAG_NONE
        self.padding_x = self.padding_y = 10
        self.old_x = self.old_y = self.old_width = 0
        self.mouse_x = self.mouse_y = 0
        self.raw_x, self.raw_y = self.lyrics_win.get_position()
        self.mouse_over = False
        self.fade_in_size = 20.0
        self.max_line_count = 2
        
        
        self.active_lyric_surfaces = [None, None]
        self.inactive_lyric_surfaces = [None, None]
        self.lyrics_text = ["深度音乐播放器 Linux Deepin", ""]
        self.lyric_rects = [gtk.gdk.Rectangle(0, 0, 0, 0), gtk.gdk.Rectangle(0, 0, 0, 0)]
        self.lyrics_xpos = [0, 0]
        self.line_alignment = [0.0, 1.0]
        self.line_percentage = [0.0, 0.0]
        self.current_line = 0
        
        for i in range(self.get_line_count()):
            self.update_lyric_surface(i)
         
        width = self.adjust_window_height()
        self.lyrics_win.set_default_size(600, int( width))           
        # Add events.
        self.lyrics_win.add_events(gtk.gdk.BUTTON_PRESS_MASK |
                                   gtk.gdk.BUTTON_RELEASE_MASK |
                                   gtk.gdk.POINTER_MOTION_MASK |
                                   gtk.gdk.ENTER_NOTIFY_MASK |
                                   gtk.gdk.LEAVE_NOTIFY_MASK)
        
        self.lyrics_win.connect("button-press-event", self.button_press) # TRY
        self.lyrics_win.connect("button_release_event", self.button_release) 
        self.lyrics_win.connect("motion-notify-event", self.motion_notify)   
        self.lyrics_win.connect("enter-notify-event", self.enter_notify)
        self.lyrics_win.connect("leave-notify-event", self.leave_notify)
        self.lyrics_win.connect("expose-event", self.expose_before)     
        gobject.timeout_add(100, self.check_mouse_leave)        
        
    def set_locked(self):    
        if config.getboolean("lyrics", "locked"):
            config.set("lyrics", "locked", "false")
            self.set_input_shape_mask(False)
        else:    
            config.set("lyrics", "locked", "true")
            self.set_input_shape_mask(True)
            
    def update_font(self, widget):        
        for i in range(self.get_line_count()):
            self.update_lyric_surface(i)
        self.lyrics_win.queue_draw()        
        x, y = self.lyrics_win.get_position()
        w, h = self.lyrics_win.get_size()
        rect = gtk.gdk.Rectangle(int(x), int(y), int(w), int(h))
        self.move_resize(self.lyrics_win, rect, DRAG_NONE)
            
    def get_locked(self):        
        return config.getboolean("lyrics", "locked")
        
    def set_dock_mode(self, value):
        if config.getboolean("lyrics", "dock_mode"):
            config.set("lyrics", "dock_mode", "false")
            self.lyrics_win.set_type_hint(gtk.WINDOW_TYPE_HINT_NORMAL)
        else:    
            config.set("lyrics", "dock_mode", "true")
            self.lyrics_win.set_type_hint(gtk.WINDOW_TYPE_HINT_DOCK)
    
    def get_dock_mode(self):
        return config.getboolean("lyrics", "dock_mode")
    
    def get_line_count(self):
        return config.getint("lyrics", "line_count")
    
    def set_line_count(self, value):
        if value in [1, 2]:    
            config.set("lyrics", "line_count", str(value))
        self.update_font(None)    
            
    def get_karaoke_mode(self):    
        return config.getboolean("lyrics", "karaoke_mode")
    
    def set_karaoke_mode(self):
        if not self.get_karaoke_mode():
            config.set("lyrics", "karaoke_mode", "true")
        else:    
            config.set("lyrics", "karaoke_mode", "false")
            self.line_percentage = [0.0, 0.0]
            for i in range(self.get_line_count()):
                self.update_lyric_surface(i)
            self.lyrics_win.queue_draw()    
        
    def get_blur_radius(self):        
        return config.getint("lyrics", "blur_radius")
    
    def set_blur_radius(self, value):
        config.set("lyrics", "blur_radius", str(value))
        
        
    def get_translucent_on_mouse_over(self):
        return config.getboolean("lyrics", "translucent_on_mouse_over")
    
    def set_translucent_on_mouse_over(self, value):
        if config.getboolean("lyrics", "translucent_on_mouse_over"):
            config.set("lyrics", "translucent_on_mouse_over", "false")
        else:    
            config.set("lyrics", "translucent_on_mouse_over", "true")
            
    def __paint_rect(self, cr, source, src_x, src_y, src_w, src_h,
                     des_x, des_y, des_w, des_h):
        ''' paint rect. '''
        cr.save()
        sw = float(des_w) / float(src_w)
        sh = float(des_h) / float(src_h)
        cr.translate(des_x, des_y)
        cr.rectangle(0, 0, des_w, des_h)
        cr.scale(sw, sh)        
        cr.clip()
        cr.set_source_pixbuf(source,  -src_x,  -src_y)
        cr.paint()
        cr.restore()
    
    def draw_bg_pixbuf(self, widget, cr):
        ''' Paint window bg. '''
        w, h = widget.get_size()
        BORDER_WIDTH = self.padding_x
        if self.is_composited:
            cr.set_operator(cairo.OPERATOR_OVER)        
            sw = self.bg_pixbuf.get_width()
            sh = self.bg_pixbuf.get_height()
            
            self.__paint_rect(cr, self.bg_pixbuf,
                              0, 0, BORDER_WIDTH, BORDER_WIDTH,
                              0, 0, BORDER_WIDTH, BORDER_WIDTH) 
            self.__paint_rect(cr, self.bg_pixbuf,
                              0, sh - BORDER_WIDTH, BORDER_WIDTH, BORDER_WIDTH,
                              0, h - BORDER_WIDTH, BORDER_WIDTH, BORDER_WIDTH)
            self.__paint_rect(cr, self.bg_pixbuf,
                              sw - BORDER_WIDTH, 0, BORDER_WIDTH, BORDER_WIDTH,
                              w - BORDER_WIDTH, 0, BORDER_WIDTH, BORDER_WIDTH)
            self.__paint_rect(cr, self.bg_pixbuf,
                              sw - BORDER_WIDTH, sh - BORDER_WIDTH, BORDER_WIDTH, BORDER_WIDTH,
                              w - BORDER_WIDTH, h - BORDER_WIDTH, BORDER_WIDTH, BORDER_WIDTH)
            self.__paint_rect(cr, self.bg_pixbuf,
                              0, BORDER_WIDTH, BORDER_WIDTH, sh - BORDER_WIDTH * 2,
                              0, BORDER_WIDTH, BORDER_WIDTH, h - BORDER_WIDTH * 2)
            self.__paint_rect(cr, self.bg_pixbuf,
                              sw - BORDER_WIDTH, BORDER_WIDTH, BORDER_WIDTH, sh - BORDER_WIDTH * 2,
                              w - BORDER_WIDTH, BORDER_WIDTH, BORDER_WIDTH, h - BORDER_WIDTH * 2)
            self.__paint_rect(cr, self.bg_pixbuf,
                              BORDER_WIDTH, 0, sw - BORDER_WIDTH * 2, BORDER_WIDTH,
                              BORDER_WIDTH, 0, w - BORDER_WIDTH * 2, BORDER_WIDTH)
            self.__paint_rect(cr, self.bg_pixbuf,
                              BORDER_WIDTH, sh - BORDER_WIDTH, sw - BORDER_WIDTH * 2, BORDER_WIDTH,
                              BORDER_WIDTH, h - BORDER_WIDTH, w - BORDER_WIDTH * 2, BORDER_WIDTH)
            self.__paint_rect(cr, self.bg_pixbuf,
                              BORDER_WIDTH, BORDER_WIDTH, sw - BORDER_WIDTH * 2, sh - BORDER_WIDTH * 2,
                              BORDER_WIDTH, BORDER_WIDTH, w - BORDER_WIDTH * 2, h - BORDER_WIDTH * 2)
        else:    
            widget.get_style().paint_box(widget.window, gtk.STATE_NORMAL, 
                                              gtk.SHADOW_IN, None, widget.get_default_widget(), 
                                              "buttondefalut", 0, 0, w, h)
        
        
    def draw_window_background(self, widget, event):    
        
        # Init
        cr = widget.window.cairo_create()
        rect = widget.allocation
        
        # Clear color to transparent window.
        if self.is_composited:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.0)
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.paint()
        else:    
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.set_source_rgb(0.9, 0.9, 0.9)
            cr.rectangle(0, 0, rect.width, rect.height)
            cr.fill()
            
        if self.mouse_over:    
            self.draw_bg_pixbuf(widget, cr)
        return True
            
    def adjust_lyrics_height(self):        
        font_height = self.render_lyrics.get_font_height()
        height = font_height * self.get_line_count() + (self.get_line_count() - 1) * self.line_padding + self.render_lyrics.get_outline_width()        
        if self.get_blur_radius():        
            height += self.get_blur_radius() * 2.0
        return height    
    
    def adjust_lyric_xpos(self, line, percentage):
        smooth = True
        w, h = self.get_lyrics_size()
        if self.active_lyric_surfaces[line] != None:
            width = self.active_lyric_surfaces[line].get_width()
        else:    
            width = 0
            
        if w >= width:    
            xpos = (w - width) * self.line_alignment[line]
        else:    
            if not self.is_composited: # self.get_dock_mode()
                smooth = False
            if smooth:    
                if percentage * width < w / 2.0:
                    xpos = 0
                elif (1.0 - percentage) * width < w / 2.0:    
                    xpos = w - width
                else:    
                    xpos = w / 2.0 - width * percentage
            else:        
                if percentage * width < w:
                    xpos = 0
                else:    
                    half_count = (percentage * width - w) / w + 1
                    xpos = -half_count * w
                    if xpos < w - width:
                        xpos = w - width
                if xpos != self.lyrics_xpos[line]:        
                    self.lyrics_xpos[line] = xpos
        return xpos            
        
    def adjust_lyric_ypos(self):    
        return self.padding_x
    
    def adjust_window_height(self):
        return self.adjust_lyrics_height() + self.padding_x * 2
    
    def get_lyrics_size(self):
        width = self.lyrics_win.allocation.width - self.padding_x * 2
        height = self.adjust_lyrics_height()
        return (width, height)
            
    def get_edge_on_point(self, widget, event):
        rect = widget.allocation
        width, height = rect.width, rect.height
        
        if event.y >= 0 and event.y <= height:
            if event.x >=0 and event.x < self.padding_x:
                return gtk.gdk.WINDOW_EDGE_WEST
            if event.x >= width - self.padding_x and event.x < width: 
                return gtk.gdk.WINDOW_EDGE_EAST
            
    def get_min_width(self):        
        return MIN_WIDTH
    
    def adjust_move_coordinate(self, widget, x, y):
        screen = widget.get_screen()
        w, h = widget.get_size()
        screen_w, screen_h = screen.get_width(), screen.get_height()
        
        if x + w > screen_w:
            x = screen_w - w
           
        if y + h > screen_h:    
            y = screen_h - h
            
        return (int(x), int(y))
            
            
    def move_resize(self, widget, rect, drag_state):        
        old_x, old_y = widget.get_position()
        old_w, old_h = widget.get_size()
        screen = widget.get_screen()
        screen_w, screen_h = screen.get_width(), screen.get_height()
        min_width = self.get_min_width()
        
        if drag_state == DRAG_EAST:
            new_x = max(0, rect.x)
            new_width = max(min(rect.width, screen_w - new_x), min_width)
        elif drag_state == DRAG_WEST:    
            new_width = max(min(rect.width, rect.x + rect.width), min_width)
            new_x = max(0, min(rect.x, self.old_x + self.old_width - new_width))
        else:    
            new_x = max(0, min(rect.x, screen_w - rect.width))
            new_width = max(rect.width, MIN_WIDTH)
            
        if rect.y + rect.height > screen_h:    
            min_h = self.adjust_window_height()
            new_height = max(min_h, screen_h - rect.y)
            new_y = max (0, screen_h - new_height)
        else:    
            new_y = max(0, rect.y)
            new_height = self.adjust_window_height()

        self.raw_x, self.raw_y = new_x, new_y    
        
        rect = gtk.gdk.Rectangle(int(new_x), int(new_y), int(new_width), int(new_height))
        self.emit("resized", rect)
        widget.resize(int(new_width), int(new_height))
        widget.move(int(new_x), int(new_y))           
        widget.queue_draw()
            
    def button_press(self, widget, event):        
        '''Button press callback.'''
        if event.button == 1 and not self.get_locked():
            edge = self.get_edge_on_point(widget, event)
            if not self.get_dock_mode():
                if edge == gtk.gdk.WINDOW_EDGE_EAST or edge == gtk.gdk.WINDOW_EDGE_WEST:
                    widget.begin_resize_drag(edge, event.button, int(event.x_root), int(event.y_root), event.time)
                else:    
                    widget.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
            else:        
                self.old_width, _ = widget.get_size()
                self.old_x, self.old_y = widget.get_position()
                self.mouse_x, self.mouse_y = event.x_root, event.y_root
                
                if edge == gtk.gdk.WINDOW_EDGE_EAST:
                    self.dock_drag_state = DRAG_EAST
                elif edge == gtk.gdk.WINDOW_EDGE_WEST:    
                    self.dock_drag_state = DRAG_WEST
                else:    
                    self.dock_drag_state = DRAG_MOVE
        return False            
    
    def motion_notify(self, widget, event):
        x = max(self.old_x + (event.x_root - self.mouse_x), 0)
        y = max(self.old_y + (event.y_root - self.mouse_y), 0)
        width, height = widget.get_size()
        if self.dock_drag_state == DRAG_MOVE:
            new_x, new_y = self.adjust_move_coordinate(widget, x, y)
            widget.move(new_x, new_y)
            emit_rect = gtk.gdk.Rectangle(int(new_x), int(new_y), int(width), int(height) )           
            self.emit("moved", emit_rect)

        elif self.dock_drag_state == DRAG_EAST:    
            rect = gtk.gdk.Rectangle(int(self.old_x), int(self.old_y), int(self.old_width + (event.x_root - self.mouse_x)), int(height))
            self.move_resize(widget, rect, DRAG_EAST)
        elif self.dock_drag_state == DRAG_WEST:
            rect = gtk.gdk.Rectangle(int(x), int(self.old_y), int(self.old_width + self.old_x - x), int(height))
            self.move_resize(widget, rect, DRAG_WEST)
        elif self.dock_drag_state == DRAG_NONE:    
            edge = self.get_edge_on_point(widget, event)
            if edge == gtk.gdk.WINDOW_EDGE_EAST:
                cursor = gtk.gdk.RIGHT_SIDE
                widget.window.set_cursor(gtk.gdk.Cursor(cursor))
            elif edge == gtk.gdk.WINDOW_EDGE_WEST:    
                cursor = gtk.gdk.LEFT_SIDE
                widget.window.set_cursor(gtk.gdk.Cursor(cursor))
            else:    
                widget.window.set_cursor(None)
        return False        
    
    def button_release(self, widget, event):
        x, y = widget.get_position()
        rect = widget.allocation
        self.dock_drag_state = DRAG_NONE    
        return False

    def enter_notify(self, widget, event):
        self.mouse_over = True
        self.emit("show-bg")
        widget.queue_draw()
        
    def leave_notify(self, widget, event):    
        # self.check_mouse_leave()
        widget.queue_draw()
        
    def expose_before(self, widget, event):    
        cr = widget.window.cairo_create()
        self.draw_window_background(widget, event)
        self.draw_lyrics(cr)
        return True
        
    def draw_lyric_surface(self, lyrics):
        if not lyrics:
            return
        width, height = self.render_lyrics.get_pixel_size(lyrics)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
        cr = cairo.Context(surface)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        self.render_lyrics.paint_text(cr, lyrics, 0, 0)
        return surface
      
    def update_lyric_rect(self, line):
        w = h = 0
        if self.active_lyric_surfaces[line] != None:
            w = self.active_lyric_surfaces[line].get_width()
            h = self.active_lyric_surfaces[line].get_height()
        font_height = self.render_lyrics.get_font_height()    
        self.lyric_rects[line] = gtk.gdk.Rectangle(
            int(self.adjust_lyric_xpos(line, self.line_percentage[line])),
            int(font_height * line * ( 1+ self.line_padding)), int(w), int(h))
        
    def update_lyric_surface(self, line):    
        self.render_lyrics.set_linear_color(COLORS_MAP["inactive"])
        self.inactive_lyric_surfaces[line] = self.draw_lyric_surface(self.lyrics_text[line])
        
        self.render_lyrics.set_linear_color(COLORS_MAP["active"])
        self.active_lyric_surfaces[line] = self.draw_lyric_surface(self.lyrics_text[line])
        self.update_lyric_rect(line)
        
    def create_text_mask(self, line, text_xpos, alpha):
        width, _ = self.get_lyrics_size()
        text_width = self.active_lyric_surfaces[line].get_width()
        if self.fade_in_size * 2 > width:
            fade_in_size = width / 2
        if self.is_composited:    
            pattern = cairo.LinearGradient(self.padding_x, 0.0, self.padding_x + width, 0.0)
            
            # Set fade in on left edge.
            if text_xpos < self.padding_x:
                pattern.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.0)
                loffset = 0.0
                if self.padding_x - text_xpos < self.fade_in_size:
                    loffset = float(self.padding_x - text_xpos) / float(width)
                else:    
                    loffset = float(self.fade_in_size) / float(width)
                    
                pattern.add_color_stop_rgba(loffset, 1.0, 1.0, 1.0, alpha)    
            else:    
                pattern.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, alpha)
                
            # Set fade out on the right edge    
            if text_xpos + text_width > self.padding_x + width:    
                roffset = 0.0
                if text_xpos + text_width - (self.padding_x + width) < self.fade_in_size:
                    roffset = 1.0  - (text_xpos + text_width - (self.padding_x + width)) / width
                else:    
                    roffset = 1.0 - float(self.fade_in_size) / width
                pattern.add_color_stop_rgba(roffset, 0.0, 0.0, 0.0, alpha)    
                pattern.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
            else:    
                pattern.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, alpha)
            return pattern    
        return None
            
        
    def draw_lyrics(self, cr):    
        alpha = 1.0
        font_height = self.render_lyrics.get_font_height()
        if self.is_composited and self.get_locked() and self.mouse_over and self.get_translucent_on_mouse_over():
            alpha = 0.3
        w, h = self.get_lyrics_size()    
        ypos = self.adjust_lyric_ypos()
        if self.get_line_count() == 1:
            start = self.current_line
            end = start + 1
        else:    
            start = 0
            end = self.max_line_count
        cr.save()    
        cr.rectangle(self.padding_x, self.padding_y, w, h)
        cr.clip()
        cr.set_operator(cairo.OPERATOR_OVER)
        for line in range(start, end):
            percentage = self.line_percentage[line]
            if self.active_lyric_surfaces[line] != None and self.inactive_lyric_surfaces[line] != None:
                width = self.active_lyric_surfaces[line].get_width()
                height = self.active_lyric_surfaces[line].get_height()
                xpos = self.adjust_lyric_xpos(line, percentage)
                xpos += self.padding_x
                text_mask = self.create_text_mask(line, xpos, alpha)
                cr.save()
                cr.rectangle(xpos, ypos, width * percentage, height)
                cr.clip()
                cr.set_source_surface(self.active_lyric_surfaces[line], xpos, ypos)
                if text_mask:
                    cr.mask(text_mask)
                else:    
                    cr.paint_with_alpha(alpha)
                cr.restore()    
                
                cr.save()
                cr.rectangle(xpos + width * percentage, ypos, width * (1.0 - percentage), height)
                cr.clip()
                cr.set_source_surface(self.inactive_lyric_surfaces[line], xpos, ypos)
                
                if text_mask:
                    cr.mask(text_mask)
                else:    
                    cr.paint_with_alpha(alpha)
                cr.restore()    
                
            ypos += font_height * ( 1 + self.line_padding)    
        cr.restore()    
        
    def set_input_shape_mask(self, disable_input):    
        if disable_input:
            region = gtk.gdk.Region()
            self.lyrics_win.window.input_shape_combine_region(region, 0, 0)
        else:    
            self.lyrics_win.window.input_shape_combine_region(self.lyrics_win.window.get_visible_region(), 0, 0)
            
    def point_in_rect(self, x, y, rect):        
        return rect.x <= x < rect.x + rect.width and rect.y <= y < rect.y + rect.height
            
    def check_mouse_leave(self):        
        root_window = gtk.gdk.get_default_root_window()
        screen_h , _ = root_window.get_size()
        rel_x, rel_y = root_window.get_pointer()[:2]
        x, y = self.lyrics_win.get_position()
        width, height = self.lyrics_win.get_size()        
        if y < 40:
            height += 40
        else:
            y -= 40
            height += 40

        rect = gtk.gdk.Rectangle(int(x), int(y), int(width), int(height))
        
        if self.dock_drag_state == DRAG_NONE and not self.point_in_rect(rel_x, rel_y, rect):
            self.mouse_over = False
            self.emit("hide-bg")
            self.lyrics_win.queue_draw()
        return True    
            
    def set_line_percentage(self, line, percentage):        
        if not self.get_karaoke_mode():
            return
        if line < 0 or line >= self.max_line_count:
            return
        if percentage == self.line_percentage[line]:
            return        
        old_percentage = self.line_percentage[line]
        self.line_percentage[line] = percentage

        if self.is_composited and percentage != old_percentage:
            old_x = self.adjust_lyric_xpos(line, old_percentage)
            new_x = self.adjust_lyric_xpos(line, percentage)
            if old_x != new_x:
                pass
        self.lyrics_win.queue_draw()    
        
    def set_current_line(self, line):    
        if 0 <= line <= self.get_line_count():
            self.current_line = line
        self.lyrics_win.queue_draw()    
            
    def set_current_percentage(self, percentage):        
        self.set_line_percentage(self.current_line, percentage)
            
    def set_line_alignment(self, line, alignment):        
        if line < 0 or line > self.get_line_count():
            return
        if alignment < 0.0:
            alignment = 0.0
        elif alignment > 1.0:
            alignment = 1.0
        self.line_alignment[line] = alignment    
        self.update_lyric_rect(line)
        self.lyrics_win.queue_draw()
        
    def set_lyric(self, line, lyric):    
        self.percentage = 0.0
        self.lyrics_text[line] = lyric
        self.update_lyric_surface(line)
        self.lyrics_win.queue_draw()
    

desktop_lyrics = LyricsWindow()        
        
LINES_MODE = 1        
SCROLL_MODE = 2
        
class ScrollLyricsWindow(object):        
    
    def __init__(self):
        self.lyrics_win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.lyrics_win.set_decorated(False)
        self.lyrics_win.set_app_paintable(True)
        colormap = self.lyrics_win.get_screen().get_rgba_colormap()
        if not colormap:
            colormap = self.lyrics_win.get_screen().get_rgb_colormap()
        self.lyrics_win.set_colormap(colormap)    
        
        # Init.
        self.percentage = 0.0
        self.whole_lyrics = None
        self.current_lyric_id = -1
        
        self.line_count = 20
        self.active_color = [0.89, 0.81, 0]
        self.inactive_color = [0.98, 0.92, 0.84]
        self.bg_color = [0, 0, 0]
        self.font_name = "serif 13"
        self.alignment = 0.5
        self.line_margin = 1
        self.padding_x = 10
        self.padding_y = 5
        self.corner_radius = 10
        self.frame_width = 7
        self.text= None
        self.scroll_mode = SCROLL_MODE
        self.seeking = False

        frame_align = gtk.Alignment()
        frame_align.set(0.0, 0.0, 1.0, 1.0)
        frame_align.set_padding(self.padding_y, self.padding_y, self.padding_x, self.padding_x)

        self.lyrics_win.add(frame_align)
          
        self.lyrics_win.connect("expose-event", self.scroll_window_expose)
        # self.lyrics_win.connect("button-press-event", self.button_press)
        # self.lyrics_win.connect("button-release-event", self.button_realse)
        # self.lyrics_win.connect("motion-notify-event", self.motion_notify)
        
        
    def scroll_window_expose(self, widget, event):    
        cr = widget.window.cairo_create()
        if self.whole_lyrics != None:
            self.__paint_lyrics(cr)
        if self.text != None:    
            print "ddd"
            self.__paint_text(cr)
        return False
    
    def set_whole_lyrics(self, lyrics):
        if not lyrics:
            return 
        self.whole_lyrics = lyrics
        self.saved_lrc_y = -1
        self.lyrics_win.queue_draw()
        
    def get_pango(self, cr):    
        context = pangocairo.CairoContext(cr)
        layout = context.create_layout()
        layout.set_font_description(pango.FontDescription(self.font_name))
        return layout
    
    
    def get_font_height(self):
        pango_context = gtk.gdk.pango_context_get()
        pango_layout = pango.Layout(pango_context)
        font_desc = pango.FontDescription(self.font_name)
        pango_layout.set_font_description(font_desc)
        metrics = pango_context.get_metrics(pango_layout.get_font_description())
        if not metrics:
            return self.line_margin
            print "cannot get font metrics!"
        else:    
            ascent = metrics.get_ascent()
            descent = metrics.get_descent()
            font_height = (ascent + descent) / pango.SCALE
            return font_height + self.line_margin
        
    def adjust_paint_pos(self):            
        if self.seeking: # try
            line_height = self.get_font_height()
            save_id = self.saved_lyric_id
            y = self.save_seek_offset - self.current_pointer_y + self.save_pointer_y
            save_id += y  / line_height
            y %= line_height
            if y < 0:
                y += line_height
                save_id -= 1
            if save_id < 0:    
                save_id = 0
                y = 0
            elif save_id > len(self.whole_lyrics):    
                save_id = len(self.whole_lyrics) - 1
                y = line_height
            return (save_id, y)
        else:
            save_id = self.current_lyric_id
            self.saved_lrc_y = self.adjust_lrc_ypos(self.percentage)
            return (save_id, self.saved_lrc_y)
        
    def adjust_lrc_ypos(self, percentage):    
        line_height = self.get_font_height()
        if self.scroll_mode == LINES_MODE:
            if percentage < 0.15:
                percentage = percentage / 0.15
            else:    
                percentage = 1
        return line_height * percentage        
        
    def adjust_line_count(self):    
        font_height = self.get_font_height()
        width, height = self.lyrics_win.get_size()
        return int(height - self.padding_y * 2) / font_height
    
    def get_active_color_ratio(self, line):
        line_height = self.get_font_height()
        current_lyric_id, lrc_y = self.adjust_paint_pos()
        percentage = float(lrc_y) / float(line_height)
        ratio = 0.0
        if line == current_lyric_id:
            ratio = (1.0 - percentage) / 0.1
            if ratio > 1.0: ratio = 1.0
            if ratio < 0.0: ratio = 0.0
            return ratio
        elif line == current_lyric_id + 1:
            ratio = (percentage - 0.9) / 0.1
            if ratio > 1.0: ratio = 1.0
            if ratio < 0.0: ratio = 0.0
        return ratio    
    
    def __paint_lyrics(self, cr):
        line_height = self.get_font_height()
        count = self.adjust_line_count()
        width, height = self.lyrics_win.get_size()
        layout = self.get_pango(cr)
        cr.save()
        cr.new_path()
        cr.rectangle(self.padding_x, 0, width - self.padding_x * 2, height - self.padding_y * 2)
        cr.close_path()
        cr.clip()
        
        current_lyric_id, lrc_y = self.adjust_paint_pos()
        begin = current_lyric_id - count / 2
        end = current_lyric_id + count / 2 + 1
        ypos = height / 2 - lrc_y - (count / 2 + 1) * line_height
        cr.set_source_rgb(*self.inactive_color)
        
        if self.whole_lyrics != None:
            # for i in range(begin, end):
            #     ypos += line_height
            #     if i < 0:
            #         continue
            #     if i >= len(self.whole_lyrics):
            #         break
            layout.set_text(self.whole_lyrics)
            cr.save()    
            # ratio = self.get_active_color_ratio(i)
            ratio = 0.0
            alpha = 1.0
            if ypos < line_height / 2.0 + self.padding_y:
                alpha = 1.0 - (line_height / 2.0 + self.padding_y - ypos) * 1.0 / line_height *2
            elif ypos > height - line_height * 1.5 - self.padding_y:    
                alpha = (height - line_height - self.padding_y - ypos) * 1.0 / line_height * 2
            if alpha < 0.0: alpha = 0.0    
            cr.set_source_rgba(self.active_color[0] * ratio + self.inactive_color[0] * (1 - ratio),
                               self.active_color[1] * ratio + self.inactive_color[0] * (1 - ratio),
                               self.active_color[2] * ratio + self.inactive_color[0] * (1 - ratio), 
                               alpha)
            cr.move_to(self.padding_x, ypos)
            cr.update_layout(layout)
            cr.restore()
                
            # cr.reset_clip()    
            cr.restore()    
            
    def __paint_text(self, cr):        
        width, height = self.lyrics_win.get_size()
        cr.save()
        cr.set_source_rgb(*self.inactive_color)
        layout = self.get_pango(cr)
        layout.set_text(self.text)
        layout.set_alignment(pango.ALIGN_CENTER)
        extent = layout.get_pixel_extents()
        x = (width - extent[0][2]) / 2
        y = (height - extent[0][3]) / 2
        if x < 0: x = 0
        if y < 0: y = 0
        cr.move_to(x, y)
        cr.update_layout(layout)
        cr.show_layout(layout)
        
    def get_pointer_edge(self, x, y, width, height, top, bottom, left, right):    
        if x < left:
            if y < top:
                ret_edge = gtk.gdk.WINDOW_EDGE_NORTH_WEST
            elif y >= height - bottom:    
                ret_edge = gtk.gdk.WINDOW_EDGE_SOUTH_WEST
            else:    
                ret_edge = gtk.gdk.WINDOW_EGDE_WEST
        elif x >= width - right:        
            if y < top:
                ret_edge = gtk.gdk.WINDOW_EDGE_NORTH_WEST
            elif y >= height - bottom:    
                ret_edge = gtk.gdk.WINDOW_EDGE_SOUTH_WEST
            else:    
                ret_edge = gtk.gdk.WINDOW_EDGE_EAST
        elif y < top:        
            ret_edge = gtk.gdk.WINDOW_EDGE_NORTH
        elif y >= height - bottom:    
            ret_edge = gtk.gdk.WINDOW_EDGE_SOUTH
        else:    
            ret = False
        if ret:
            return ret
        
    def begin_move_resize(self, widget, event):    
        pass
    

    def set_progress(self, lyric_id, percentage):    
        saved_lyric_id = self.current_lyric_id
        self.current_lyric_id = lyric_id
        self.percentage = percentage
        if saved_lyric_id != lyric_id or self.saved_lrc_y != self.adjust_lrc_ypos(percentage):
            self.lyrics_win.queue_draw()
            
    def set_text(self, text):        
        self.text = text
        self.lyrics_win.queue_draw()
        
    def get_current_lyric_id(self):    
        return self.current_lyric_id
    
    def set_font_name(self, font_name):
        self.font_name = font_name
        self.lyrics_win.queue_draw()
        
    def get_font_name(self):    
        return self.font_name

    
