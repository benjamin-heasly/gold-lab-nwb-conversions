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
    $ pip install .
    $ python
    >>> from pyramid import hello
    >>> hello.plot()
    """

    # use matplotlib in interactive mode instead of blocking on plt.show().
    plt.ion()

    fig, ax = plt.subplots()
    th = np.linspace(0, 2*np.pi, 512)
    ax.set_ylim(-1.5, 1.5)

    ln, = ax.plot(th, np.sin(th))

    start_time = time.time()
    uptime = time.time() - start_time
    while uptime < timeout and plt.get_fignums():
        # check for trial data
        time.sleep(.01)

        # redraw the plot
        ln.set_ydata(np.sin(th + uptime))
        ln.figure.canvas.draw_idle()

        # respond to plot window events, including user inputs
        ln.figure.canvas.flush_events()

        uptime = time.time() - start_time

    plt.close(fig)
