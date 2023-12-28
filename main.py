import pyglet
pyglet.options['shadow_window'] = False

import cProfile
from datetime import datetime

from src.window import Window




pr = cProfile.Profile()
pr.enable()

w = Window()
pyglet.app.run()

pr.disable()
dt = datetime.now().strftime("%Y-%m-%d %Hh%Mm%S")
pr.dump_stats(f'./Profiler Results {dt}.prof')