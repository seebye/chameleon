# chameleon
Chameleon is a color picker for X11 written in python

1. Installation
2. Dependencies
3. Conversion
4. Usage examples
5. Preview

## 1. Installation

```bash
# pip3 install moving-chameleon
```

## 2. Dependencies

* python3-Xlib
* docopt
* Pillow

## 3. Conversion

Chameleon allows you to apply changes to the colors while selecting them.  
Conversion supports:

- rgb, hls, hsv, yiq
- +, -, *, /, //, %, <<, >>, &, |, ^
- pi, e
- and the python math module:  
  int, float, abs, min, max,  
  acos, acosh, asin, asinh, atan,  
  atan2, atanh, ceil, copysign, cos,  
  cosh, degrees, erf, erfc, exp,  
  expm1, fabs, floor, fmod, frexp,  
  gamma, gcd, hypot, ldexp,  
  lgamma, log, log10, log1p, log2,  
  modf, pow, radians, sin, sinh,  
  sqrt, tan, tanh, trunc

## 4. Usage examples

- Print the selected color as rgb:  
  `chameleon -f "rgb({0:d}, {1:d}, {2:d})"`
- Selecting three colors:  
  `chameleon -c 3`
- Selecting four colors with the same lightness:  
  ```chameleon -c 4 -C "hls(h, l1, s)" "`chameleon`"```
- Selecting two colors with the same hue:  
  ```chameleon -c 2 -C "hls(h1, l, s)" "`chameleon`"```
- Selecting five colors with 0.5 lightness or more:  
  `chameleon -c 5 -C "hls(h, min(0.5, l), s)"`
- Selecting two colors with the lightness of a previous selection and a constant hue:  
  ```chameleon -c 2 -C "hls(h1, l2, s)" "#ff0000" "`chameleon`"```

## 5. Preview

![Chameleon Preview](preview.gif?raw=true)
