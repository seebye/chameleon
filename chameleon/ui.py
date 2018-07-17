import contextlib
import itertools
import math

from Xlib import X, display, Xcursorfont
import PIL.Image
import chameleon.colors as colors

@contextlib.contextmanager
def create_font_cursor(display, which):
    """Implementation of libX11 XCreateFontCursor,
    creates one of the default cursors.

    Arg:
        display: Xlib display
        which: one of Xcursorfont

    Yields:
        the acquired cursor object
    """
    # see: https://github.com/mirror/libX11/blob/78851f6a03130e3c720b60c3cbf96f8eb216d741/src/Cursor.c # noqa
    black, white = (0, 0, 0), (65535, 65535, 65535)
    font, cursor = None, None

    try:
        font = display.open_font('cursor')
        cursor = font.create_glyph_cursor(
            font, which, which + 1,
            black, white)
        yield cursor
    finally:
        if cursor:
            cursor.free()
        if font:
            font.close()


@contextlib.contextmanager
def pick_coordinate(display, cursor):
    """Changes the cursor and grabs the pointer for every window.

    Args:
        display: Xlib display
        cursor: cursor object or X.NONE
    """
    try:
        display.screen().root.grab_pointer(
            0, X.PointerMotionMask | X.ButtonReleaseMask | X.ButtonPressMask,
            X.GrabModeAsync, X.GrabModeAsync, X.NONE,
            cursor, X.CurrentTime)
        display.flush()
        yield
    finally:
        display.ungrab_pointer(0)
        display.flush()


def events(display):
    """Returns an generator which yields incoming x11 events"""
    return (display.next_event() for _ in itertools.count())


def get_pointer_position(root, event=None):
    """Extracts the pointer position from the event,
    falls back to root.query_pointer on failure.

    Args:
        root: Xlib root window
        event: Xlib event

    Returns:
        (tuple of int): (x, y) pointer position
    """
    try:
        return event.root_x, event.root_y
    except AttributeError:
        reply = root.query_pointer()
        return reply.root_x, reply.root_y


def get_pixel(wnd, x, y):
    """Determines the pixel at the passed position.

    Arg:
        wnd: Xlib window
        x (int): self-explanatory
        y (int): self-explanatory

    Returns:
        (tuple of int): (r, g, b) color tuple
    """
    image = wnd.get_image(x, y, 1, 1, X.ZPixmap, 0xffffffff)
    if isinstance(image.data, str):
        image.data = image.data.encode()
    return PIL.Image.frombytes("RGB", (1, 1), image.data, "raw", "BGRX")\
        .getcolors()[0][1]


class ColorWindow:
    """Window class used to display a color,
    e.g. a selected one or a live preview

    Attributes:
        margin (int): distance to the pointer
        size (int): window size, not changeable
        size_border (int): border size
    """

    def __init__(self, display, margin, size, size_border, color=(0, 0, 0)):
        self._last_color = color
        self._display = display
        self._screen = display.screen()
        self._root = self._screen.root
        self.margin = margin + int(size / 2)
        self.size = size
        self.size_border = size_border
        self._wnd = None
        self._gc = None
        res = self._root.get_geometry()
        self.screen_width, self.screen_height = res.width, res.height

    def map(self):
        """Creates a window and gc if they don't exists already,
        and maps it afterwards.

        Returns:
            X11 window
        """
        if not self._wnd:
            self._wnd = self._root.create_window(
                0, 0, self.size, self.size, 0,
                self._screen.root_depth,
                X.InputOutput, X.CopyFromParent,
                event_mask=X.ExposureMask,
                colormap=X.CopyFromParent,
                override_redirect=True)
            self._gc = self._wnd.create_gc()
        self._wnd.map()
        self._display.flush()
        return self._wnd

    def unmap(self):
        """Unmaps the window if it exists."""
        if self._wnd:
            self._wnd.unmap()
            self._wnd.destroy()
            self._wnd = None
            self._display.flush()

    def move(self, x, y):
        """Moves the window based on the given position
        and tries to keep it visible while doing so.

        Args:
            x (int): x-cursor position
            y (int): y-cursor position
        """
        # Cartesian coordinate system / x, y from center
        x_center = (x - self.screen_width / 2)
        y_center = -(y - self.screen_height / 2)
        # inverted radians
        rad = math.atan2(-y_center, -x_center)
        offset_y = int(self.margin * -math.sin(rad))
        offset_x = int(self.margin * math.cos(rad))

        self._wnd.configure(
            # - size/2 => move the object at its center
            x=x - int(self.size / 2) + offset_x,
            y=y - int(self.size / 2) + offset_y
        )

    def _set_color(self, r, g, b):
        """Changes the foreground color of the gc object.

        Args:
            r (int): red
            g (int): green
            b (int): blue
        """
        self._gc.change(foreground=((0xff << (8 * 3)) |
                                    (int(r) << (8 * 2)) |
                                    (int(g) << (8 * 1)) |
                                    (int(b) << (8 * 0))))

    def _draw_rectangle(self, x, y, width, height):
        """Draws a rectangle with the current foreground color on the window.

        Args:
            x (int): self-explainatory
            y (int): self-explainatory
            width (int): self-explainatory
            height (int): self-explainatory
        """
        self._wnd.fill_rectangle(self._gc, x, y, width, height)

    def _draw_border(self, r, g, b):
        """Draws a lightened or darkened border
        based on the passed color on the window.

        Args:
            r (int): red
            g (int): green
            b (int): blue
        """
        self._set_color(*colors.adjust_brightness(45, r, g, b))

        for rect in ((0, 0, self.size_border, self.size),
                     (0, 0, self.size, self.size_border),
                     (self.size - self.size_border, 0, self.size, self.size),
                     (0, self.size - self.size_border, self.size, self.size)):
            self._draw_rectangle(*rect)

    def draw(self, rgb=None):
        """Redraws the window.

        Args:
            rgb (tuple of int): new color or None
        """
        r, g, b = rgb or self._last_color
        self._last_color = (r, g, b)
        self._set_color(r, g, b)
        self._draw_rectangle(0, 0, self.size, self.size)
        self._draw_border(r, g, b)


class WindowMapper(contextlib.ContextDecorator, list):
    """Ensures unmapping of windows"""

    def __init__(self, *wnds):
        self._mapped = False
        self.extend(wnds)

    def append(self, wnd):
        if self._mapped:
            wnd.map()
        super().append(wnd)

    def __enter__(self):
        for wnd in self:
            wnd.map()
        self._mapped = True
        return self

    def __exit__(self, *args):
        for wnd in self:
            wnd.unmap()
