
class InteraccioFigura:
    """Gestor d'interacció amb una figura de Matplotlib per a un canal concret."""

    def __init__(self, ch):
        self.ch = ch
        self.press = None
        self._setup_interaccions()

    def _setup_interaccions(self):
        """Connecta els events del ratolí amb les funcions corresponents."""
        fig = self.ch.figure
        fig.canvas.mpl_connect('scroll_event', self._zoom)
        fig.canvas.mpl_connect('button_press_event', self._on_press)
        fig.canvas.mpl_connect('button_release_event', self._on_release)
        fig.canvas.mpl_connect('motion_notify_event', self._on_motion)

    def _zoom(self, event, base_scale=1.1):
        xdata, ydata = event.xdata, event.ydata
        xlim, ylim = self.ch.XYlims

        if xdata is None or ydata is None:
            return

        scale_factor = 1 / base_scale if event.button == 'up' else base_scale
        midaX = (xlim[1] - xlim[0]) * scale_factor
        midaY = (ylim[1] - ylim[0]) * scale_factor

        relx = (xlim[1] - xdata) / (xlim[1] - xlim[0])
        rely = (ylim[1] - ydata) / (ylim[1] - ylim[0])

        xlow = xdata - midaX * (1 - relx)
        xhigh = xdata + midaX * relx
        ylow = ydata - midaY * (1 - rely)
        yhigh = ydata + midaY * rely

        # Limitem als marges del canal
        if 0 < xlow < xhigh < self.ch.midaBase[0]:
            xlim = (xlow, xhigh)
        if 0 < ylow < yhigh < self.ch.midaBase[1]:
            ylim = (ylow, yhigh)

        self.ch.XYlims = xlim, ylim

    def _on_press(self, event):
        if event.inaxes != self.ch.ax:
            return
        self.press = (event.xdata, event.ydata)

    def _on_release(self, event):
        self.press = None

    def _on_motion(self, event):
        if self.press is None or event.inaxes != self.ch.ax:
            return

        xlim, ylim = self.ch.XYlims
        dx = event.xdata - self.press[0]
        dy = event.ydata - self.press[1]

        new_xlim = (xlim[0] - dx, xlim[1] - dx)
        new_ylim = (ylim[0] - dy, ylim[1] - dy)

        if new_xlim[0] >= 0 and new_xlim[1] <= self.ch.midaBase[0]:
            xlim = new_xlim
        if new_ylim[0] >= 0 and new_ylim[1] <= self.ch.midaBase[1]:
            ylim = new_ylim

        self.ch.XYlims = xlim, ylim