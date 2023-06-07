import time
import numpy as np
import matplotlib.pyplot as plt


def hello():
    return "hello"


def plot(timeout: float = 10):
    """Proof of concept for concurrency with matplotlib.

    Want pyramid GUI mode to be able to juggle at the same time:
     - checking for new trial updates
     - updating plots for each new trial
     - responding to GUI user inputs like resizing figures or pressing buttons/widgets
     - responding to GUI window closing so we can exit

    Reading:
    https://matplotlib.org/stable/users/explain/interactive_guide.html#explicitly-spinning-the-event-loop
    https://stackoverflow.com/questions/7557098/matplotlib-interactive-mode-determine-if-figure-window-is-still-displayed

    It seems like this should work if pyramid has a loop that cycles through these tasks.
    A cycle duration of tens of miliseconds should feel responsive.
    It means checking for trial updates should block with a short timeout and/or poll.

    So here's a simplified example where I'll try things out.

    I'm running this manually from a local terminal, in this "pyramid" dir, in the gold_nwb conda environment.
    $ conda activate gold_nwb
    $ cd pyramid
    $ pip install .
    $ python
    >>> from pyramid import hello
    >>> hello.plot()
    """

    # use matplotlib in interactive mode instead of blocking on plt.show().
    plt.ion()

    fig1, ax1 = plt.subplots()
    th1 = np.linspace(0, 2*np.pi, 512)
    ax1.set_ylim(-1.5, 1.5)
    ln1, = ax1.plot(th1, np.sin(th1))

    fig2, ax2 = plt.subplots()
    th2 = np.linspace(0, 2*np.pi, 512)
    ax2.set_ylim(-1.5, 1.5)
    ln2, = ax2.plot(th2, np.cos(th2))

    start_time = time.time()
    uptime = time.time() - start_time
    while uptime < timeout and plt.get_fignums():
        # check for trial data
        time.sleep(.01)

        # update and redraw each plot
        if plt.fignum_exists(fig1.number):
            ln1.set_ydata(np.sin(th1 + uptime))
            fig1.canvas.draw_idle()
            fig1.canvas.flush_events()

        # update and redraw each plot
        if plt.fignum_exists(fig2.number):
            ln2.set_ydata(np.cos(th2 + uptime))
            fig2.canvas.draw_idle()
            fig2.canvas.flush_events()

        uptime = time.time() - start_time

    if plt.fignum_exists(fig1.number):
        plt.close(fig1)

    if plt.fignum_exists(fig2.number):
        plt.close(fig2)

# What's a "plot" going to do?
# Init a managed figure
# Init with experiment and subject info
# Init user axes / subplots and stash references
# Init user lines etc. and stash references
# Init user other state and stash?
# Check if managed figures still exists
# Update with experiment info, subject info, current trial, trial extraction info
# Update user lines etc.
# Update user other state?
# Redraw managed figure canvas
# Flush managed figure canvas events
# Close managed figure
