import ctypes
import os
from abc import ABC

import pyglet

from src.constants import (TEXTURE_N_TILES_PER_ROW, 
                           TEXTURE_TILE_SIZE_NORMALIZED, 
                           TEXTURE_TILE_PADDING, 
                           TILEMAP_N_ROWS, 
                           TILEMAP_N_COLS,
                           SHADERS_FOLDER)


class _AbstractRenderer(ABC):

    def __init__(self, tilemap):
        self._tilemap = tilemap
        self._texture_id = tilemap.texture_id

        self._shader_handle = None
        self._vbo_handle = None
        self._vao_handle = None

        self._create_shader()
        self._allocate_vbo_vao()
        self.recalculate()

    def _create_shader(self):
        raise NotImplementedError

    def draw(self):
        raise NotImplementedError

    def _update_vbo(self):
        raise NotImplementedError

    def _update_vao(self):
        raise NotImplementedError

    def _compile_shader_program(self, sources_and_shadertypes):
        self._shader_handle = pyglet.gl.glCreateProgram()

        handles = []
        temp = ctypes.c_int(0)
        for source, shader_type in sources_and_shadertypes:
            source = source.encode('utf8')
            handle = pyglet.gl.glCreateShader(shader_type)
            handles.append(handle)
            source_buffer_pointer = ctypes.cast(ctypes.c_char_p(source), ctypes.POINTER(ctypes.c_char))
            pyglet.gl.glShaderSource(handle, 1, ctypes.byref(source_buffer_pointer), ctypes.c_int(len(source)))
            pyglet.gl.glCompileShader(handle)

            # Check if error occurred.
            pyglet.gl.glGetShaderiv(handle, pyglet.gl.GL_COMPILE_STATUS, ctypes.byref(temp))
            if not temp:
                # Retrieve the log length.
                pyglet.gl.glGetShaderiv(handle, pyglet.gl.GL_INFO_LOG_LENGTH, ctypes.byref(temp))
                # Create a buffer for the log.
                buffer = ctypes.create_string_buffer(temp.value)
                # Retrieve the log text.
                pyglet.gl.glGetShaderInfoLog(handle, temp, None, buffer)
                # Raise error with log content.
                raise RuntimeError(buffer.value.decode())
            
            pyglet.gl.glAttachShader(self._shader_handle, handle)
            
        pyglet.gl.glLinkProgram(self._shader_handle)

        # Check if error occurred.
        pyglet.gl.glGetProgramiv(self._shader_handle, pyglet.gl.GL_LINK_STATUS, ctypes.byref(temp))
        if not temp:
            # Retrieve the log length.
            pyglet.gl.glGetProgramiv(self._shader_handle, pyglet.gl.GL_INFO_LOG_LENGTH, ctypes.byref(temp))
            # Create a buffer for the log.
            buffer = ctypes.create_string_buffer(temp.value)
            # Retrieve the log text.
            pyglet.gl.glGetProgramInfoLog(self._shader_handle, temp, None, buffer)
            # Raise error with log content.
            raise RuntimeError(buffer.value.decode())

        for handle in handles:
            pyglet.gl.glDetachShader(self._shader_handle, handle)
            pyglet.gl.glDeleteShader(handle)

    def _allocate_vbo_vao(self):
        buffer_id = pyglet.gl.GLuint()
        pyglet.gl.glGenBuffers(1, buffer_id)
        self._vbo_handle = buffer_id.value

        array_id = pyglet.gl.GLuint()
        pyglet.gl.glGenVertexArrays(1, array_id)
        self._vao_handle = array_id.value
        
    def recalculate(self):
        self._update_vbo()
        self._update_vao()

    def _prepare_params_to_set_uniform(self, name, values, ctype_type):
        name = ctypes.create_string_buffer(name.encode('utf-8'))
        location = pyglet.gl.glGetUniformLocation(self._shader_handle, name)

        try:
            values = (ctype_type * len(values))(*values)
        except:
            values = ctype_type(values)

        return location, values

    def _get_projection_matrix(self):
        # Input vertex coordinates have origin on the top left with x increasing as we go right and y increasing as we go down.
        # Each tile has a width and a height of 1.

        # Model matrix so that origin is at the center of the tilemap.
        # Tilemap x_range = (- TILEMAP_N_COLS / 2, TILEMAP_N_COLS / 2), y_range = (- TILEMAP_N_ROWS / 2, TILEMAP_N_ROWS / 2)
        model_matrix = pyglet.math.Mat4.from_translation(pyglet.math.Vec3(-TILEMAP_N_COLS / 2, -TILEMAP_N_ROWS / 2, 0))

        # View matrix should not change anything.
        view_matrix  = pyglet.math.Mat4()
        
        # Projection matrix scales so that tilemap fits tightly into clip-space: ranging from -1 to +1 in each coordinate.
        proj_matrix  = pyglet.math.Mat4.from_scale(pyglet.math.Vec3(2 / TILEMAP_N_COLS, 2 / TILEMAP_N_ROWS, 0))
        
        return proj_matrix @ view_matrix @ model_matrix
    
    def __del__(self):
        try:
            pyglet.gl.glDeleteVertexArrays(1, ctypes.c_ulong(self._vao_handle))
            pyglet.gl.glDeleteBuffers(1, ctypes.c_ulong(self._vbo_handle))
            pyglet.gl.glDeleteProgram(self._shader_handle)
        except:
            # When closing window the OpenGL context is deallocated before this destructor gets called.
            # This raises an exception but should not cause memory leaks given the program is exiting.
            pass




class VertexBufferedRenderer(_AbstractRenderer):

    def _create_shader(self):
        vert_source = open(os.path.join(SHADERS_FOLDER, 'VertexBufferedRenderer.vert')).read()
        frag_source = open(os.path.join(SHADERS_FOLDER, 'VertexBufferedRenderer.frag')).read()

        self._compile_shader_program([(vert_source, pyglet.gl.GL_VERTEX_SHADER),
                                      (frag_source, pyglet.gl.GL_FRAGMENT_SHADER)])


    def draw(self):
        pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, self._texture_id)
        pyglet.gl.glBindVertexArray(self._vao_handle)

        projection = self._get_projection_matrix()

        location, projection = self._prepare_params_to_set_uniform('projection', projection, ctypes.c_float)
        pyglet.gl.glProgramUniformMatrix4fv(self._shader_handle, location, 1, False, projection)
        
        pyglet.gl.glUseProgram(self._shader_handle)
        n_vertices_per_tile = 6 # Each tile has 2 triangles, each with 3 vertices
        pyglet.gl.glDrawArrays(pyglet.gl.GL_TRIANGLES, 0, len(self._tilemap) * n_vertices_per_tile)


    def _update_vbo(self):
        pyglet.gl.glBindBuffer(pyglet.gl.GL_ARRAY_BUFFER, self._vbo_handle)

        float_count = len(self._tilemap) * 6 * 2 * 2
        # for each tile
        # there are 6 vertices (two triangles, each with 3 vertices)
        # each vertex has two components: Position and Texcoord
        # each component has two fields: x and y

        vertex_data = [0.0] * float_count

        i = 0
        for x in range(TILEMAP_N_COLS):
            for y in range(TILEMAP_N_ROWS):
                tile = self._tilemap[y, x]

                # Calculate normalized texture coordinates. Use padding to mitigate the lines-between tiles bug
                # which is caused by the lack of tile margins in the texture atlas.
                tx0 = (tile %  TEXTURE_N_TILES_PER_ROW) * TEXTURE_TILE_SIZE_NORMALIZED + TEXTURE_TILE_PADDING
                ty0 = (tile // TEXTURE_N_TILES_PER_ROW) * TEXTURE_TILE_SIZE_NORMALIZED + TEXTURE_TILE_PADDING
                tSize = TEXTURE_TILE_SIZE_NORMALIZED - TEXTURE_TILE_PADDING * 2

                # vertex 0 (top left)
                vertex_data[i + 0] = x # position x
                vertex_data[i + 1] = y # position y
                vertex_data[i + 2] = tx0 # texcoord x
                vertex_data[i + 3] = ty0 # texcoord y
                i += 4

                # vertex 1 (top right)
                vertex_data[i + 0] = x + 1 # position x
                vertex_data[i + 1] = y # position y
                vertex_data[i + 2] = tx0 + tSize # texcoord x
                vertex_data[i + 3] = ty0 # texcoord y
                i += 4

                # vertex 2 (bottom left)
                vertex_data[i + 0] = x # position x
                vertex_data[i + 1] = y + 1 # position y
                vertex_data[i + 2] = tx0 # texcoord x
                vertex_data[i + 3] = ty0 + tSize # texcoord y
                i += 4

                # vertex 3 (top right)
                vertex_data[i + 0] = x + 1 # position x
                vertex_data[i + 1] = y # position y
                vertex_data[i + 2] = tx0 + tSize # texcoord x
                vertex_data[i + 3] = ty0 # texcoord y
                i += 4

                # vertex 4 (bottom left)
                vertex_data[i + 0] = x # position x
                vertex_data[i + 1] = y + 1 # position y
                vertex_data[i + 2] = tx0 # texcoord x
                vertex_data[i + 3] = ty0 + tSize # texcoord y
                i += 4

                # vertex 5 (bottom right)
                vertex_data[i + 0] = x + 1 # position x
                vertex_data[i + 1] = y + 1 # position y
                vertex_data[i + 2] = tx0 + tSize # texcoord x
                vertex_data[i + 3] = ty0 + tSize # texcoord y
                i += 4

        l = len(vertex_data)
        vertex_data = (ctypes.c_float * l)(*vertex_data)

        pyglet.gl.glBufferData(pyglet.gl.GL_ARRAY_BUFFER, l * ctypes.sizeof(ctypes.c_float), vertex_data, pyglet.gl.GL_STATIC_DRAW)


    def _update_vao(self):
        pyglet.gl.glBindVertexArray(self._vao_handle)
        
        pyglet.gl.glBindBuffer(pyglet.gl.GL_ARRAY_BUFFER, self._vbo_handle)
        
        n_coords_vertex_position     = 2
        n_coords_texture_coordinates = 2

        pyglet.gl.glEnableVertexAttribArray(0)
        pyglet.gl.glVertexAttribPointer(0, # Attribute number given in vertex shader layout()
                                        n_coords_vertex_position, # Number of elements needed to build attribute (here vec2)
                                        pyglet.gl.GL_FLOAT, # Type of attribute
                                        False, # Do not normalize
                                        ctypes.sizeof(ctypes.c_float) * (n_coords_vertex_position + n_coords_texture_coordinates), # Stride to reach start of next vertex
                                        0) # No offset: first elements in vertex array are position, not texcoords.

        pyglet.gl.glEnableVertexAttribArray(1)
        pyglet.gl.glVertexAttribPointer(1, # Attribute number given in vertex shader layout()
                                        n_coords_texture_coordinates, # Number of elements needed to build attribute (here vec2)
                                        pyglet.gl.GL_FLOAT, # Type of attribute
                                        False, # Do not normalize
                                        ctypes.sizeof(ctypes.c_float) * (n_coords_vertex_position + n_coords_texture_coordinates), # Stride to reach start of next vertex
                                        ctypes.sizeof(ctypes.c_float) * n_coords_vertex_position) # Offset by the number of elements in vertex position (previous attribute)
        

class GeomBufferedRenderer(_AbstractRenderer):

    def _create_shader(self):
        vert_source = open(os.path.join(SHADERS_FOLDER, 'GeometryShaderRenderer.vert')).read()
        frag_source = open(os.path.join(SHADERS_FOLDER, 'GeometryShaderRenderer.frag')).read()
        geom_source = open(os.path.join(SHADERS_FOLDER, 'GeometryShaderRenderer.geom')).read() \
                          .replace('{TEXTURE_N_TILES_PER_ROW}'     , str(TEXTURE_N_TILES_PER_ROW)) \
                          .replace('{TEXTURE_TILE_SIZE_NORMALIZED}', str(TEXTURE_TILE_SIZE_NORMALIZED)) \
                          .replace('{TEXTURE_TILE_PADDING}'        , str(TEXTURE_TILE_PADDING))

        self._compile_shader_program([(vert_source, pyglet.gl.GL_VERTEX_SHADER),
                                      (frag_source, pyglet.gl.GL_FRAGMENT_SHADER),
                                      (geom_source, pyglet.gl.GL_GEOMETRY_SHADER)])

    def draw(self):
        pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, self._texture_id)
        pyglet.gl.glBindVertexArray(self._vao_handle)

        projection = self._get_projection_matrix()

        location, projection = self._prepare_params_to_set_uniform('projection', projection, ctypes.c_float)
        pyglet.gl.glProgramUniformMatrix4fv(self._shader_handle, location, 1, False, projection)
        
        location, n_cols = self._prepare_params_to_set_uniform('n_cols', TILEMAP_N_COLS, ctypes.c_int)
        pyglet.gl.glProgramUniform1i(self._shader_handle, location, n_cols)

        pyglet.gl.glUseProgram(self._shader_handle)
        pyglet.gl.glDrawArrays(pyglet.gl.GL_POINTS, 0, len(self._tilemap))
        
        
    def _update_vbo(self):
        pyglet.gl.glBindBuffer(pyglet.gl.GL_ARRAY_BUFFER, self._vbo_handle)

        vertex_data = self._tilemap.map

        l = len(vertex_data)
        vertex_data = (ctypes.c_uint32 * l)(*vertex_data)

        pyglet.gl.glBufferData(pyglet.gl.GL_ARRAY_BUFFER, l * ctypes.sizeof(ctypes.c_uint32), vertex_data, pyglet.gl.GL_STATIC_DRAW)


    def _update_vao(self):
        pyglet.gl.glBindVertexArray(self._vao_handle)
        
        pyglet.gl.glBindBuffer(pyglet.gl.GL_ARRAY_BUFFER, self._vbo_handle)
        
        pyglet.gl.glEnableVertexAttribArray(0)
        pyglet.gl.glVertexAttribIPointer(0, 1, pyglet.gl.GL_UNSIGNED_INT, ctypes.sizeof(ctypes.c_uint32), 0)