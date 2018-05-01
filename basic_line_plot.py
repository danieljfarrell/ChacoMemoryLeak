""" Script for reproducing memory leak when Chaco updates the axis ranges.

    Version
    -------

    Versions of traits tested (leak could also exist in other version):

    >>> traits.__version__
    '4.5.0'
    >>> traitsui.__version__
    '4.5.1'
    >>> chaco.__version__
    '4.5.0'
    >>> enable.__version__
    '4.5.1'

    Usage
    -----
    
    Run script from the command line.

        `python run_line_plot.py`

    Optionally change the refresh rate on line 95.

"""
import time
import numpy as np
import os
import psutil
from traits.api import HasTraits, Instance
from traitsui.api import View, Item
from chaco.api import Plot, ArrayPlotData
from enable.api import ComponentEditor
import threading
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('chaco.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class LinePlot(HasTraits):

    plot = Instance(Plot)

    plot_data = Instance(ArrayPlotData)

    traits_view = View(
        Item('plot',editor=ComponentEditor(), show_label=False),
        width=500, height=500, resizable=True, title="Chaco Plot")

    def _plot_data_default(self):
        xmin = np.random.uniform(-0.1, 0.1)
        xmax = np.random.uniform(0.9, 1.1)
        x = np.linspace(xmin, xmax, 2**11)
        y = np.sin(np.pi*x)**100
        return ArrayPlotData(x=x, y=y)

    def update_data(self):
        # Want a random dataset where the ranges change every update
        xmin = np.random.uniform(-0.1, 0.1)
        xmax = np.random.uniform(0.9, 1.1)
        x = np.linspace(xmin, xmax, 2**11)
        y = np.sin(np.pi*x)**100
        y *= np.random.uniform(0.8, 1.2, x.shape[0])
        self.plot_data.set_data("x", x)
        self.plot_data.set_data("y", y)

    def _plot_default(self):
        plot = Plot(self.plot_data)
        plot.plot(("x", "y"), type="line", color="blue")
        plot.title = "Title"
        return plot

    def autoscale_axis(self):
        x = self.plot_data.get_data("x")
        y = self.plot_data.get_data("y")
        xmin, xmax = np.min(x), np.max(x)
        ymin, ymax = np.min(y), np.max(y)
        self.plot.range2d.x_range.low = xmin
        self.plot.range2d.x_range.high = xmax
        self.plot.range2d.y_range.low = ymin - np.abs(0.1*ymin)
        self.plot.range2d.y_range.high = ymax + np.abs(0.1*ymax)


def threaded_update():
    def update_loop(line_plot):
        time.sleep(5.0)  # wait for UI to load
        iter_idx = 0
        while True:
            time.sleep(1.0/30.0)  # 60Hz
            if iter_idx % 1000 == 0:
                # log memory usage
                usage = float(psutil.Process(os.getpid()).memory_info().rss)*1e-6
                info = '#[{}] MB:{:f}'.format(iter_idx, usage)
                logger.warning(info)
            line_plot.update_data()
            line_plot.autoscale_axis()
            iter_idx += 1

    plot = LinePlot()
    thd = threading.Thread(target=update_loop, args=(plot,))
    thd.daemon = True
    thd.start()
    plot.configure_traits()


def timed_update():
    from pyface.timer.api import Timer

    def update_loop(line_plot):
        line_plot.update_data()
        # shouldn't need this
        # line_plot.autoscale_axis()

    def log_memory():
        # log memory usage
        usage = float(psutil.Process(os.getpid()).memory_info().rss)*1e-6
        info = '#[{}] MB:{:f}'.format(-1, usage)
        logger.warning(info)

    plot = LinePlot()
    millisecs = int(1000.0/30.0)  # ~30Hz
    update_timer = Timer(millisecs, update_loop, plot)
    log_timer = Timer(int(1000.0*10.0), log_memory)
    update_timer.Start()
    log_timer.Start()
    plot.configure_traits()

if __name__ == "__main__":
    timed_update()
