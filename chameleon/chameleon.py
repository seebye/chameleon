#!/usr/bin/env python3
# chameleon is a simple color picker for X11
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Usage:
    chameleon [options] [COLORS...]

Colors:
    Input: RGB-Hex-String, e.g. '#ff0033'
    Output: RGB, formatted according to the format option

Options:
    -m <px>, --margin <px>     Distance to the cursor in px [default: 50]
    -S <px>, --separator <px>  Distance between color windows [default: 20]
    -s <px>, --size <px>       Size of a color window [default: 30]
    -b <px>, --border <px>     Border size of a color window [default: 4]
    -c <n>, --count <n>        Number of colors to select [default: 1]
    -f <fmt>, --format <fmt>   Color format [default: #{0:02x}{1:02x}{2:02x}]
    -C <e>, --conversion <e>   Color conversion,
                               e.g. enforcing the same lightness as the first
                               input color: hls(h, l1, s)
                               [default: rgb(r, g, b)]

Conversion:
    Special functions:
        Referencing these functions will lead to the declaration of
        color variables.

        The current color will be declared with and without suffix.
        So for rgb it would be r, g, b and r0, g0, b0.
        The first input color will be available as r1, g1, b1.
        Subsequent colours will be named by the same structure.

        rgb: declares colors as r [0-255], g [0-255], b [0-255]
        hls: declares colors as h [0-360], l [0-100], s [0-100]
        hsv: declares colors as h [0-360], s [0-100], v [0-100]
        yiq: declares colors as y [0-1], i, q

    Operators:
        +, -, *, /, //, %, <<, >>, &, |, ^

    Functions:
        int, float, abs, min, max,
        acos, acosh, asin, asinh, atan,
        atan2, atanh, ceil, copysign, cos,
        cosh, degrees, erf, erfc, exp,
        expm1, fabs, floor, fmod, frexp,
        gamma, gcd, hypot, ldexp,
        lgamma, log, log10, log1p, log2,
        modf, pow, radians, sin, sinh,
        sqrt, tan, tanh, trunc

    Constants:
        pi, e

License:
    This program comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it
    under certain conditions.
"""
import itertools

from Xlib import X, display, Xcursorfont
import docopt
import chameleon.colors as colors
import chameleon.ui as ui


def singleton(cls):
    """Creates argless singletons"""
    return cls()


@singleton
class Params:
    """Helper class which allows to access passed arguments"""
    # lambda needed to access the right docstring
    __dict = docopt.docopt((lambda: __doc__)())
    __default = docopt.docopt((lambda: __doc__)(), argv=[])
    __typed = {}

    def _init_key(self, key):
        val_def = Params.__default.get(key)
        val = Params.__dict[key]

        try:
            int(val_def)
        except (TypeError, ValueError):
            return val
        return int(val)

    def __getattr__(self, name):
        key = name if name in Params.__dict \
            else '--' + name
        val = Params.__typed.get(key)

        if not val:
            val = self._init_key(key)
            Params.__typed[key] = val

        return val


def main():
    disp = display.Display()
    root = disp.screen().root
    wnd = ui.ColorWindow(disp, Params.margin, Params.size, Params.border)
    count = itertools.count()
    calc = colors.ColorCalculator(Params.conversion)
    rgbs = colors.parse_hex_rgb(*Params.COLORS)

    with ui.WindowMapper(wnd) as mapper,\
            ui.create_font_cursor(disp, Xcursorfont.tcross) as cursor,\
            ui.pick_coordinate(disp, cursor):
        for e in ui.events(disp):
            x, y = ui.get_pointer_position(root, e)
            rgb = calc.calc(*itertools.chain(
                (ui.get_pixel(root, x, y),), rgbs))

            if e.type == X.ButtonPress and e.detail == X.MOUSE_BUTTON_LEFT:
                print(Params.format.format(*rgb))
                if next(count) + 1 >= Params.count:
                    break

                mapper.append(ui.ColorWindow(
                    disp,
                    (len(mapper) * (Params.size + Params.separator) +
                        Params.margin),
                    Params.size,
                    Params.border,
                    rgb))

            elif e.type in (X.Expose, X.MotionNotify):
                for w in mapper:
                    if e.type == X.Expose:
                        w.draw()
                    w.move(x, y)
                wnd.draw(rgb)
