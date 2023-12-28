#version 330 core

uniform int n_cols;

layout (location = 0) in uint aTileId;

out VS_OUT {
    uint tileId;
} vs_out;

void main()
{
    int i = gl_VertexID;
    float x = float(int(i % n_cols));
    float y = float(int(i / n_cols));
    gl_Position = vec4(x, y, 0.0, 1.0);
    
    vs_out.tileId = aTileId;
}