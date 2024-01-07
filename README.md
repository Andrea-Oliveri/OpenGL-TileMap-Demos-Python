# OpenGL-TileMap-Demos-Python

## Project Overview

This repository offers a port into Python of some renderers from [davudk/OpenGL-TileMap-Demos](https://github.com/davudk/OpenGL-TileMap-Demos/tree/master), originally written in C#.

As a result, it provides Python code to render a tilemap much faster than what would be possible with immediate rendering.

Vertex-buffered rendering and Geometry Shader Rendering in particular are implemented in [src/renderer.py](src/renderer.py)

Vertex-buffered rendering is implemented both using native OpenGL calls and using Pyglet's `ShaderProgram` class.


## Topline Profiler Results
On a simple benchmark with a TileMap composed of 36 rows and 28 columns, the following results were obtained.
Reported are the cumulative time, per call, in seconds:

| **Renderer**      | **draw()** | **recalculate()** |
|-------------------|------------|-------------------|
| _Geometry Shader_ | 0.0002031  | 0.0001807         |
| _Vertex-Buffered_ | 0.0001621  | 0.006053          |
| _Vertex-Buffered (Pyglet)_ | 0.0004581  | 0.003455          |
| _Instantaneous_   | 0.2491     | 0                 |




## References
For more detailed explainations on each renderer, please refer to the original repository [davudk/OpenGL-TileMap-Demos](https://github.com/davudk/OpenGL-TileMap-Demos/tree/master).

To learn more about OpenGL and shaders, I found very helpful [Learn OpenGL](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&ved=2ahUKEwj2wZOgs7KDAxV-7rsIHe3kAmIQFnoECAkQAQ&url=https%3A%2F%2Flearnopengl.com%2F&usg=AOvVaw1PZwEycHmOOF22dKz8geD1&opi=89978449).

To learn more about Pyglet, please reference their [documentation](https://pyglet.readthedocs.io/en/latest/) and their [Github repository](https://github.com/pyglet/pyglet). 

## Repository Structure

This directory contains the following files and directories:

* [**main.py**](main.py): Main Python script used to run the app.
* [**src**](src): Directory collecting all additional Python scripts and custom packages needed to run the app.
* [**Assets**](Assets): Directory containing the image atlas used in this demo. 
* [**Shaders**](Shaders): Directory containing the GLSL code for the different shader implementations.
* [**README.md**](README.md): The Readme file you are currently reading.

## Getting Started

### 0) Python Environment

The Python enviroment used for this project was kept as simple as possible.

An environment containing the required packages with compatible versions can be created as follows:

```bash
conda create -n tilemap_demo python=3.12.0
conda activate tilemap_demo
pip install pyglet==2.0.8 snakeviz==2.2.0
```

### 1) Run

To run the demo app, simply activate the correct conda environment and, from the same directory as the [**main.py**](main.py) file run:

```bash
python main.py
```

Use the whitespace key to toggle between the different types of renderers. Use any other key to randomly generate a new tilemap.


### 2) Visualize profile results

cProfile is used to generate a performance dump each time the application is run. This allows to compare the speed of the different rendering techniques. Note that the time needed by Pyglet to draw the FPS on screen may represent a sizeable portion of the rendering time and is therefore advised to remove the FPS counter when benchmarking your implementations.

To visualize the results in the profiler dump, run:

```bash
snakeviz "Profiler Results {...}.prof"
```
