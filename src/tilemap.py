
from random import randint

import pyglet

from src.constants import TEXTURE_ATLAS_PATH, TEXTURE_TILE_SIZE_PX, TILEMAP_N_ROWS, TILEMAP_N_COLS


class TileMap:

    def __init__(self):
        self._texture   = pyglet.image.load(TEXTURE_ATLAS_PATH).get_texture()
        
        # Set nearest neighbour interpolation.
        # This is best for pixelated art and also helps fixing the lines-between tiles bug
        # which is caused by the lack of tile margins in the texture atlas.
        pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, self._texture.id)
        pyglet.gl.glTexParameteri(pyglet.gl.GL_TEXTURE_2D, pyglet.gl.GL_TEXTURE_MAG_FILTER, pyglet.gl.GL_NEAREST)
        # ------------------------------------------------
        
        self._rows = TILEMAP_N_ROWS
        self._cols = TILEMAP_N_COLS
        self._max_value = (self._texture.width // TEXTURE_TILE_SIZE_PX) * (self._texture.height // TEXTURE_TILE_SIZE_PX) - 1

        self._map = [0] * self._rows * self._cols

    def _cvt_idx(self, idx):
        row, col = idx

        if row > self._rows or row < 0:
            raise IndexError
        if col > self._cols or col < 0:
            raise IndexError
        return row * self._cols + col

    def __getitem__(self, idx):
        idx = self._cvt_idx(idx)
        return self._map[idx]

    def __setitem__(self, idx, value):
        idx = self._cvt_idx(idx)

        if value > self._max_value or value < 0:
            raise IndexError

        self._map[idx] = value

    def __len__(self):
        return len(self._map)

    def random_fill(self):
        for row in range(self._rows):
            for col in range(self._cols):
                self[row, col] = randint(0, self._max_value)

    @property
    def texture_id(self):
        return self._texture.id
    
    @property
    def map(self):
        return self._map