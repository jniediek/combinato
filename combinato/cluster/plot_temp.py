# JN 2015-01-13
from __future__ import absolute_import, print_function, division

import matplotlib.pyplot as mpl
from .. import options


def plot_temperatures(tree, used_points):
    """
    show which clusters were selected in temperature plot
    """
    upto_line = options['MaxClustersPerTemp'] + 5
    fig = mpl.figure(figsize=options['tempfigsize'])
    plot = fig.add_subplot(1, 1, 1)
    plot.grid(True)
    plot.plot(tree[:, 1], tree[:, 4:upto_line])
    plot.set_yscale('log')
    plot.set_xlim((tree[0, 1], tree[-1, 1]))

    for row, col, color in used_points:
        x = tree[row, 1]
        y = tree[row, col]
        plot.scatter(x, y, color=color)
        plot.text(x, y, '{:.0f}'.format(y))

    return fig
