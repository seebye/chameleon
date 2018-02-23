import itertools
import ast
import operator
import math
import copy
import math
import colorsys


def parse_hex_rgb(*hex_colors):
    """Parses a rgb hex string e.g. '#ff00ff'
    and converts it to a int tuple.
    """
    return [tuple(int(hexrgb[i:i+2], 16) for i in (1, 3 ,5))
            for hexrgb in hex_colors
            if hexrgb]

def colorsys_rgb(r, g, b):
    """Converts normal rgb [0-255] to
    colorsys rgb [0-1]
    """
    return tuple(i / 255 for i in (r, g, b))


def default_rgb(r, g, b):
    """Converts colorsys rgb [0-1] to
    normal rgb [0-255]
    """
    return tuple(int(i * 255) for i in (r, g, b))

def colorsys_hsv_hls(h, s, vl):
    """Converts normal hsv/hls [0-360], [0-1], [0-1] to
    colorsys rgb [0-1], [0-1], [0-1]
    """
    return h / 360, s, vl

def default_hsv_hls(h, s, vl):
    """Converts colorsys hsv/hls [0-1], [0-1], [0-1] to
    normal hsv/hls [0-360], [0-1], [0-1]
    """
    return h * 360, s, vl


def adjust_brightness(percent, r, g, b):
    """Converts the rgb color to hsv and
    increases or decreases the brightness
    by brightness * percent / 100.

    Args:
        percent (int): targeted brightness difference
        r (int): red
        g (int): green
        b (int): blue

    Returns:
        (tuple of int): (r, g, b) lightened or darkened color
    """
    hsv = list(colorsys.rgb_to_hsv(*colorsys_rgb(r, g, b)))
    part = hsv[2] * percent / 100
    hsv[2] = max(0, hsv[2] - part) \
        if hsv[2] > .5 \
        else min(1, hsv[2] + part)
    return default_rgb(*colorsys.hsv_to_rgb(*hsv))



def color_space(name, *args):
    """Decoration for usable colorspace,
    uses the methods name to name variables and functions.
    E.g. rgb -> rgb(r % 50, g, b), hsv -> hsv(180, s, v)
    """
    def tmp(self):
        return self.change_colorspace(name, *args)
    return property(fget=tmp)

class ColorCalculator(ast.NodeVisitor):
    _BIN_OP = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Invert: operator.neg,
        ast.LShift: operator.lshift,
        ast.RShift: operator.rshift,
        ast.BitOr: operator.or_,
        ast.BitAnd: operator.and_,
        ast.BitXor: operator.xor,
    }
    _UNARY_OP = {
        ast.USub: lambda n: -n,
        ast.UAdd: lambda n: n,
    }
    _DEFAULT_SCOPE = {**{
        fct.__name__: fct for fct in (
            int, float, abs, min, max,
            math.acos, math.acosh, math.asin, math.asinh, math.atan,
            math.atan2, math.atanh, math.ceil, math.copysign, math.cos,
            math.cosh, math.degrees, math.erf, math.erfc, math.exp,
            math.expm1, math.fabs, math.floor, math.fmod, math.frexp,
            math.gamma, math.gcd, math.hypot, math.ldexp,
            math.lgamma, math.log, math.log10, math.log1p, math.log2,
            math.modf, math.pow, math.radians, math.sin, math.sinh,
            math.sqrt, math.tan, math.tanh, math.trunc
        )
    }, **{
        'pi': math.pi,
        'e': math.e,
    }, **{
        name: color_space(name, *args)
        for name, args in {
            'rgb': ((lambda *id: id), (lambda *id: id), default_rgb, colorsys_rgb),
            'yiq': (colorsys.rgb_to_yiq, colorsys.yiq_to_rgb, (lambda *id: id), (lambda *id: id)),
            'hls': (colorsys.rgb_to_hls, colorsys.hls_to_rgb, default_hsv_hls, colorsys_hsv_hls),
            'hsv': (colorsys.rgb_to_hsv, colorsys.hsv_to_rgb, default_hsv_hls, colorsys_hsv_hls),
        }.items()
    }}

    def __init__(self, exp):
        self.tree = ast.parse(exp)

    def calc(self, *rgbs):
        self.rgbs = rgbs
        self._scope = copy.copy(ColorCalculator._DEFAULT_SCOPE)
        # reset values
        '''self._scope.update({
            k + str(suffix): None
            for suffix in itertools.chain(('',), range(len(rgbs)))
            for colorspace in ('hsv', 'hls', 'rgb', 'yiq')
            for k in colorspace
        })'''
        return self.visit(self.tree.body[0])

    def _register_colors(self, name, colors):
        """Declares & defines the colors
        within the calculators scope.
        First letter = first color component and so on..
        The first color will be declared twice,
        as 'first letter' and 'first letter0'.
        """
        for suffix in itertools.chain(('',), range(len(colors))):
            for component in range(len(name)):
                #import sys
                #print(suffix,'-', component, name, colors, name[component] + str(suffix), sys.stderr)
                self._scope[name[component] + str(suffix)] = colors[int(suffix or 0)][component]

    def change_colorspace(self, cs, rgb_to_cs, cs_to_rgb, default_cs, colorsys_cs):
        """Defines variables for the colorspace
        and returns the function which converts it
        back to rgb.
        """
        colors = [default_cs(*rgb_to_cs(*colorsys_rgb(*rgb)))
                  for rgb in self.rgbs]
        self._register_colors(cs, colors)
        return lambda a, b, c: default_rgb(*cs_to_rgb(*colorsys_cs(a, b, c)))

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        return self._BIN_OP[type(node.op)](left, right)

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        return self._UNARY_OP[type(node.op)](operand)

    def visit_Call(self, node):
        func = self.visit(node.func)
        args = (self.visit(i) for i in node.args)
        return func(*args)

    def visit_Name(self, node):
        tmp = self._scope[node.id]
        if isinstance(tmp, property):
            tmp = tmp.fget(self)
        return tmp

    def visit_Num(self, node):
        return node.n

    def visit_Expr(self, node):
        return self.visit(node.value)

    def generic_visit(self, node):
        raise ArithmeticError("can't calculate with " + type(node))
