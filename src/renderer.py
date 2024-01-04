import ctypes
import os
from abc import ABC, abstractmethod

import pyglet

from src.constants import (TEXTURE_TILE_SIZE_PX,
                           TEXTURE_N_TILES_PER_ROW, 
                           TEXTURE_TILE_SIZE_NORMALIZED, 
                           TEXTURE_TILE_PADDING, 
                           TILEMAP_N_ROWS, 
                           TILEMAP_N_COLS,
                           SHADERS_FOLDER)



class _AbstractRenderer(ABC):
    @abstractmethod
    def __init__(self, tilemap):
        raise NotImplementedError

    @abstractmethod
    def recalculate(self):
        raise NotImplementedError

    @abstractmethod
    def draw(self):
        raise NotImplementedError

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




class NaiveInstantaneousRenderer(_AbstractRenderer):

    def __init__(self, tilemap):
        self._tilemap = tilemap

        texture = tilemap.texture
        self._image_grid = pyglet.image.ImageGrid(texture, texture.height // TEXTURE_TILE_SIZE_PX, texture.width // TEXTURE_TILE_SIZE_PX)
        self._image_grid = pyglet.image.TextureGrid(self._image_grid)

        for im in self._image_grid:
            im.anchor_x = 0
            im.anchor_y = im.height        

    def recalculate(self):
        return

    def draw(self):

        for x in range(TILEMAP_N_COLS):
            for y in range(TILEMAP_N_ROWS):
                tile = self._tilemap[y, x]
                image_tile = self._image_grid[tile]

                x_ = x * TEXTURE_TILE_SIZE_PX
                y_ = (y + 1) * TEXTURE_TILE_SIZE_PX

                image_tile.blit(x_, y_, width = TEXTURE_TILE_SIZE_PX, height = TEXTURE_TILE_SIZE_PX)





class _OpenGLRenderer(_AbstractRenderer, ABC):

    def __init__(self, tilemap):
        self._tilemap = tilemap
        self._texture_id = tilemap.texture.id

        self._shader_handle = None
        self._vbo_handle = None
        self._vao_handle = None

        self._create_shader()
        self._allocate_vbo_vao()
        self.recalculate()

    @abstractmethod
    def _create_shader(self):
        raise NotImplementedError

    @abstractmethod
    def draw(self):
        raise NotImplementedError

    @abstractmethod
    def _update_vbo(self):
        raise NotImplementedError

    @abstractmethod
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
    
    def __del__(self):
        try:
            pyglet.gl.glDeleteVertexArrays(1, ctypes.c_ulong(self._vao_handle))
            pyglet.gl.glDeleteBuffers(1, ctypes.c_ulong(self._vbo_handle))
            pyglet.gl.glDeleteProgram(self._shader_handle)
        except:
            # When closing window the OpenGL context is deallocated before this destructor gets called.
            # This raises an exception but should not cause memory leaks given the program is exiting.
            pass





class VertexBufferedRenderer(_OpenGLRenderer):

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
        




class GeomBufferedRenderer(_OpenGLRenderer):

    def _create_shader(self):
        vert_source = open(os.path.join(SHADERS_FOLDER, 'GeometryShaderRenderer.vert')).read()
        frag_source = open(os.path.join(SHADERS_FOLDER, 'GeometryShaderRenderer.frag')).read()
        geom_source = open(os.path.join(SHADERS_FOLDER, 'GeometryShaderRenderer.geom')).read() \
                          .replace('{TEXTURE_N_TILES_PER_ROW}'     , f'{TEXTURE_N_TILES_PER_ROW}u') \
                          .replace('{TEXTURE_TILE_SIZE_NORMALIZED}', f'{TEXTURE_TILE_SIZE_NORMALIZED}') \
                          .replace('{TEXTURE_TILE_PADDING}'        , f'{TEXTURE_TILE_PADDING}')

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





class Pyglet_VertexBufferedRenderer(_AbstractRenderer):
    def __init__(self, tilemap):
        self._tilemap = tilemap
        self._texture_id = tilemap.texture.id

        self._shader_program = None
        self._vertex_list = None

        self._create_shader()
        self._allocate_vbo_vao()
        self.recalculate()
        

    def _create_shader(self):
        vert_source = open(os.path.join(SHADERS_FOLDER, 'VertexBufferedRenderer.vert')).read()
        frag_source = open(os.path.join(SHADERS_FOLDER, 'VertexBufferedRenderer.frag')).read()

        vert_shader = pyglet.graphics.shader.Shader(vert_source, 'vertex')
        frag_shader = pyglet.graphics.shader.Shader(frag_source, 'fragment')
        self._shader_program = pyglet.graphics.shader.ShaderProgram(vert_shader, frag_shader)


    def _allocate_vbo_vao(self):
        vertex_count = len(self._tilemap) * 6
        # for each tile
        # there are 6 vertices (two triangles, each with 3 vertices)

        self._vertex_list = self._shader_program.vertex_list(vertex_count, pyglet.gl.GL_TRIANGLES)


    def recalculate(self):
        self._update_vbo()


    def _update_vbo(self):
        float_count = len(self._vertex_list.aPosition)

        position_data = [0.0] * float_count
        texcoord_data = [0.0] * float_count

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
                position_data[i + 0] = x # position x
                position_data[i + 1] = y # position y
                texcoord_data[i + 0] = tx0 # texcoord x
                texcoord_data[i + 1] = ty0 # texcoord y
                i += 2

                # vertex 1 (top right)
                position_data[i + 0] = x + 1 # position x
                position_data[i + 1] = y # position y
                texcoord_data[i + 0] = tx0 + tSize # texcoord x
                texcoord_data[i + 1] = ty0 # texcoord y
                i += 2

                # vertex 2 (bottom left)
                position_data[i + 0] = x # position x
                position_data[i + 1] = y + 1 # position y
                texcoord_data[i + 0] = tx0 # texcoord x
                texcoord_data[i + 1] = ty0 + tSize # texcoord y
                i += 2

                # vertex 3 (top right)
                position_data[i + 0] = x + 1 # position x
                position_data[i + 1] = y # position y
                texcoord_data[i + 0] = tx0 + tSize # texcoord x
                texcoord_data[i + 1] = ty0 # texcoord y
                i += 2

                # vertex 4 (bottom left)
                position_data[i + 0] = x # position x
                position_data[i + 1] = y + 1 # position y
                texcoord_data[i + 0] = tx0 # texcoord x
                texcoord_data[i + 1] = ty0 + tSize # texcoord y
                i += 2

                # vertex 5 (bottom right)
                position_data[i + 0] = x + 1 # position x
                position_data[i + 1] = y + 1 # position y
                texcoord_data[i + 0] = tx0 + tSize # texcoord x
                texcoord_data[i + 1] = ty0 + tSize # texcoord y
                i += 2

        self._vertex_list.aPosition[:] = position_data
        self._vertex_list.aTexCoord[:] = texcoord_data


    def draw(self):
        self._shader_program.use()
        pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, self._texture_id)

        projection = self._get_projection_matrix()
        self._shader_program.uniforms['projection'] = projection

        self._vertex_list.draw(pyglet.gl.GL_TRIANGLES)
        self._shader_program.stop()