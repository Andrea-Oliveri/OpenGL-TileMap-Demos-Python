#version 330 core
                          
uniform mat4 projection;

in VS_OUT {
    uint tileId;
} gs_in[];

out vec2 texCoord;

layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

void main() {
    uint tileId = gs_in[0].tileId;
    float tileX = float(tileId % {TEXTURE_N_TILES_PER_ROW}) * {TEXTURE_TILE_SIZE_NORMALIZED} + {TEXTURE_TILE_PADDING};
    float tileY = float(tileId / {TEXTURE_N_TILES_PER_ROW}) * {TEXTURE_TILE_SIZE_NORMALIZED} + {TEXTURE_TILE_PADDING};

    const float B = {TEXTURE_TILE_PADDING};
    const float S = {TEXTURE_TILE_SIZE_NORMALIZED} - 2 * {TEXTURE_TILE_PADDING};

    gl_Position = projection * gl_in[0].gl_Position;
    texCoord = vec2(tileX, tileY);
    EmitVertex();

    gl_Position = projection * (gl_in[0].gl_Position + vec4(1.0, 0.0, 0.0, 0.0));
    texCoord = vec2(tileX + S, tileY);
    EmitVertex();

    gl_Position = projection * (gl_in[0].gl_Position + vec4(0.0, 1.0, 0.0, 0.0));
    texCoord = vec2(tileX, tileY + S);
    EmitVertex();

    gl_Position = projection * (gl_in[0].gl_Position + vec4(1.0, 1.0, 0.0, 0.0));
    texCoord = vec2(tileX + S, tileY + S);
    EmitVertex();

    EndPrimitive();
}