# -*- coding: utf-8 -*-

import pyglet

from src.tilemap import TileMap
from src.renderer import VertexBufferedRenderer, GeomBufferedRenderer, NaiveInstantaneousRenderer, Pyglet_VertexBufferedRenderer

from src.constants import WINDOW_MINIMUM_SIZE



class Window(pyglet.window.Window):
    def __init__(self):
        super().__init__(*WINDOW_MINIMUM_SIZE, vsync = False, resizable = True)
        self.set_minimum_size(*WINDOW_MINIMUM_SIZE)
        
        self._init_gl()

        self._tilemap = TileMap()
        self._tilemap.random_fill()

        self._renderer = None
        self._renderers_cls_list = [Pyglet_VertexBufferedRenderer, GeomBufferedRenderer, VertexBufferedRenderer, NaiveInstantaneousRenderer ]
        self.set_renderer(self._renderers_cls_list[0])


    def _init_gl(self):
        # Set background color to black.
        pyglet.gl.glClearColor(0, 0, 0, 1)

        # Enable transparency.
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)


    def on_resize(self, width, height):
        desired_width, desired_height = WINDOW_MINIMUM_SIZE

        scale = min(width // desired_width, height // desired_height)
        viewport_width  = desired_width * scale
        viewport_height = desired_height * scale

        pad_x = (width  - viewport_width ) / 2
        pad_y = (height - viewport_height) / 2

        self.viewport = (pad_x, pad_y, viewport_width, viewport_height)

        #self.projection = pyglet.math.Mat4.orthogonal_projection(-1, +1, -1, +1, -255, 255)

        return pyglet.event.EVENT_HANDLED   # Don't call the default handler


    def on_key_press(self, symbol, modifiers):
        if symbol != pyglet.window.key.SPACE:
            self._tilemap.random_fill()
            self._renderer.recalculate()
            return
        
        i, = [idx for idx, e in enumerate(self._renderers_cls_list) if isinstance(self._renderer, e)]
        i = (i+1) % len(self._renderers_cls_list)
        
        self.set_renderer(self._renderers_cls_list[i])
            

    def set_renderer(self, cls):
        print('Currently active:', cls.__name__)
        self._renderer = cls(self._tilemap)


    def on_draw(self):
        self.clear()
        self._renderer.draw()

        self._draw_fps_counter()


    def _draw_fps_counter(self):
        if not hasattr(self, 'fps_display'):
            self.fps_display = pyglet.window.FPSDisplay(window=self)
            self.fps_display.label = pyglet.text.Label('', x=70, y=135, font_size=24, bold=True, color = (255, 0, 0, 255))

        self.fps_display.draw()
        
        # Pyglet has a bad habit of disabling transparency.
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
