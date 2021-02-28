# -*- coding: utf-8 -*-

__title__ = "Curves to Surface"
__author__ = "Christophe Grellier (Chris_G)"
__license__ = "LGPL 2.1"
__doc__ = "Interpolate curves to surface"

# import FreeCAD
import Part
from . import _utils
from .BSplineAlgorithms import SurfAdapterView


def _find_knot(curve, knot, tolerance=1e-15):
    for i in range(1, curve.NbKnots + 1):
        if abs(knot - curve.getKnot(i)) < tolerance:
            return i
    return -1


def match_knots(curves, tolerance=1e-15):
    "Set the knot sequence of each curve to a common one"
    first = curves[0]
    for cur_idx in range(1, len(curves)):
        for kno_idx in range(1, curves[cur_idx].NbKnots + 1):
            k = curves[cur_idx].getKnot(kno_idx)
            mult = curves[cur_idx].getMultiplicity(kno_idx)
            fk = _find_knot(first, k, tolerance)
            if fk > -1:
                om = first.getMultiplicity(fk)
                if om < mult:
                    first.increaseMultiplicity(fk, mult)
                    print("Increased mult of knot # {} from {} to {}".format(fk, om, mult))
            else:
                first.insertKnot(k, mult)
                print("Inserting knot {} mult {}".format(k, mult))
    for cur_idx in range(1, len(curves)):
        for kno_idx in range(1, first.NbKnots + 1):
            k = first.getKnot(kno_idx)
            mult = first.getMultiplicity(kno_idx)
            fk = _find_knot(curves[cur_idx], k, tolerance)
            if fk > -1:
                curves[cur_idx].increaseMultiplicity(fk, mult)
            else:
                curves[cur_idx].insertKnot(k, mult)


def U_linear_surface(surf):
    "Returns a copy of surf that is linear in the U direction"
    poles = [surf.getPoles()[0], surf.getPoles()[-1]]
    bs = Part.BSplineSurface()
    bs.buildFromPolesMultsKnots(poles,
                                [2, 2], surf.getVMultiplicities(),
                                [0, 1], surf.getVKnots(),
                                False, surf.isVPeriodic(),
                                1, surf.VDegree)
    return bs


def print_main_poles(surf):
    pts = surf.getPoles()
    print("O: {}\nU: {}\nV: {}".format(pts[0][0],
                                       pts[-1][0],
                                       pts[0][-1]))


class CurvesToSurface:
    def __init__(self, curves):
        self.curves = self._convert_to_bsplines(curves)
        self._periodic = False
        self._params = None
        self.all_closed = None
        self.force_periodic_if_closed = True

    @property
    def Periodic(self):
        "Periodicity in the lofting direction"
        return self._periodic

    @Periodic.setter
    def Periodic(self, p):
        if self._periodic is not bool(p):
            self._periodic = bool(p)
            if self._params is not None:
                print("Periodicity changed. You must recompute parameters.")

    @property
    def Parameters(self):
        "List of interpolating parameters of the curves"
        return self._params

    @Parameters.setter
    def Parameters(self, par):
        if isinstance(par, (list, tuple)):
            pf = 0
            if self._periodic:
                pf = 1
            if len(par) == len(self.curves) + pf:
                self._params = par
            else:
                print("Wrong number of parameters")

    @property
    def Surface(self):
        "Builds and returns the loft surface"
        self.build_surface()
        return self._surface

    @property
    def Face(self):
        "Builds and returns the loft face"
        return self.Surface.toShape()

    def _convert_to_bsplines(self, curves):
        nc = []
        for c in curves:
            if isinstance(c, Part.Edge):
                nc.append(c.Curve.toBSpline())
            elif isinstance(c, Part.Wire):
                nc.append(c.approximate())
            else:
                nc.append(c.toBSpline())
        return nc

    def _print_curves(self):
        print([c.Degree for c in self.curves])
        for c in self.curves:
            print(c.getKnots())
        for c in self.curves:
            print(c.getMultiplicities())

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, len(self.curves))

    def check_all_closed(self):
        self.all_closed = True
        for c in self.curves:
            if not c.isClosed():
                self.all_closed = False
        if self.all_closed and self.force_periodic_if_closed:
            for c in self.curves:
                if not c.isPeriodic():
                    c.setPeriodic()
                    print("Forcing periodic : {}".format(c.isPeriodic()))
                else:
                    print("Already periodic")

    def auto_twist(self, num=36):
        if self.all_closed is None:
            self.check_all_closed()
        if self.all_closed is False:
            return
        for cur_idx in range(1, len(self.curves)):
            pts1 = self.curves[cur_idx - 1].discretize(num)
            pts2 = self.curves[cur_idx].discretize(num)
            pts2 *= 2
            min_dist = 1e50
            good_offset = 0
            for offset_idx in range(num):
                total_length = 0
                for pt_idx in range(num):
                    ls = Part.makeLine(pts1[pt_idx], pts2[pt_idx + offset_idx])
                    total_length += ls.Length
                if total_length < min_dist:
                    min_dist = total_length
                    good_offset = offset_idx
            knot = self.curves[cur_idx].parameter(pts2[good_offset])
            self.curves[cur_idx].insertKnot(knot, 1)
            fk = _find_knot(self.curves[cur_idx], knot, 1e-15)
            if fk > -1:
                self.curves[cur_idx].setOrigin(fk)
            else:
                print("Something went wrong")

    def match_degrees(self):
        "Match all curve degrees to the highest one"
        max_degree = 0
        for c in self.curves:
            max_degree = max(max_degree, c.Degree)
        for c in self.curves:
            c.increaseDegree(max_degree)

    def orient_curves(self, c1, c2):
        """orient_curves(c1, c2)
        Orient c2 in same direction as c1 """
        if c1.isClosed():
            fp1 = 0.75 * c1.FirstParameter + 0.25 * c1.LastParameter
            lp1 = 0.25 * c1.FirstParameter + 0.75 * c1.LastParameter
        else:
            fp1 = c1.FirstParameter
            lp1 = c1.LastParameter
        if c2.isClosed():
            fp2 = 0.75 * c2.FirstParameter + 0.25 * c2.LastParameter
            lp2 = 0.25 * c2.FirstParameter + 0.75 * c2.LastParameter
        else:
            fp2 = c2.FirstParameter
            lp2 = c2.LastParameter
        ls1 = Part.makeLine(c1.value(fp1), c2.value(fp2))
        ls2 = Part.makeLine(c1.value(lp1), c2.value(lp2))
        d1 = ls1.distToShape(ls2)[0]
        ls1 = Part.makeLine(c1.value(fp1), c2.value(lp2))
        ls2 = Part.makeLine(c1.value(lp1), c2.value(fp2))
        d2 = ls1.distToShape(ls2)[0]
        if d1 < d2:
            c2.reverse()
            return True

    def auto_orient(self):
        "Automatically match curves orientation"
        for i in range(1, len(self.curves)):
            if self.orient_curves(self.curves[i - 1], self.curves[i]):
                print("Reversed curve #{}".format(i))

    def normalize_knots(self):
        "Set all curves knots to the [0,1] interval"
        for c in self.curves:
            fp = c.FirstParameter
            lp = c.LastParameter
            if (not fp == 0.0) or (not lp == 1.0):
                normalized_knots = [(k - fp) / (lp - fp) for k in c.getKnots()]
                c.setKnots(normalized_knots)

    def _parameters_at_poleidx(self, fac=1.0, idx=1):
        if idx < 1:
            idx = 1
        elif idx > self.curves[0].NbPoles:
            idx = self.curves[0].NbPoles
        pts = [c.getPole(idx) for c in self.curves]
        if self.Periodic and pts[0].distanceToPoint(pts[-1]) > 1e-7:  # we need to add the first point as the end point
            pts.append(pts[0])
        params = [0.0]
        for i in range(1, len(pts)):
            p = pts[i] - pts[i - 1]
            pl = pow(p.Length, fac)
            params.append(params[-1] + pl)
        return [p / params[-1] for p in params]

    def set_parameters(self, fac=1.0):
        "Compute an average parameters list from parametrization factor in [0.0, 1.0]"
        params_array = []
        for pole_idx in range(1, self.curves[0].NbPoles + 1):
            params_array.append(self._parameters_at_poleidx(fac, pole_idx))
        params = []
        for idx in range(len(params_array[0])):
            pl = [params_array[i][idx] for i in range(len(params_array))]
            params.append(sum(pl) / len(pl))
        print("Average parameters : {}".format(params))
        self.Parameters = params

    def interpolate(self):
        "interpolate the poles of the curves and build the surface"
        if self.Parameters is None:
            self.set_parameters(1.0)
        poles_array = []
        bs = Part.BSplineCurve()
        for pole_idx in range(1, self.curves[0].NbPoles + 1):
            pts = [c.getPole(pole_idx) for c in self.curves]
            bs.interpolate(Points=pts, Parameters=self.Parameters, PeriodicFlag=self.Periodic)
            poles_array.append(bs.getPoles())
        self._surface = Part.BSplineSurface()
        self._surface.buildFromPolesMultsKnots(poles_array,
                                               self.curves[0].getMultiplicities(), bs.getMultiplicities(),
                                               self.curves[0].getKnots(), bs.getKnots(),
                                               self.curves[0].isPeriodic(), bs.isPeriodic(),
                                               self.curves[0].Degree, bs.Degree)

    def build_surface(self):
        "Make curves compatible and build surface"
        self.match_degrees()
        # self.auto_orient()
        self.auto_twist()
        self.auto_orient()
        self.normalize_knots()
        match_knots(self.curves)
        self.interpolate()


class Gordon:
    """Gordon Surface algorithm on 3 surfaces : S1 + S2 - S3"""
    def __init__(self, s1, s2, s3):
        self.s1 = s1
        self.s2 = s2
        self.s3 = s3

    def check_bounds(self):
        u0, u1, v0, v1 = self.s1.bounds()
        if not self.s2.bounds() == (u0, u1, v0, v1):
            print("S1 and S2 bounds don't match")
            return False
        if not self.s3.bounds() == (u0, u1, v0, v1):
            print("S1 and S3 bounds don't match")
            return False
        return True

    def check_corner(self, uv, tol=1e-7):
        u, v = uv
        p1 = self.s1.value(u, v)
        if self.s2.value(u, v).distanceToPoint(p1) > tol:
            print("S1 and S2 points @({}, {}) don't match".format(u, v))
            return False
        if self.s3.value(u, v).distanceToPoint(p1) > tol:
            print("S1 and S3 points @({}, {}) don't match".format(u, v))
            return False
        return True

    def check_corners(self, tolerance=1e-7):
        u0, u1, v0, v1 = self.s1.bounds()
        check = True
        for p in [(u0, v0), (u0, v1), (u1, v0), (u1, v1)]:
            check = check and self.check_corner(p, tol=tolerance)
        return check

    def input_surfaces_match(self, tol=1e-7):
        return self.check_bounds() and self.check_corners(tol)

    def match_degrees_and_knots(self):
        max_Udegree = 0
        max_Vdegree = 0
        for c in [self.s1, self.s2, self.s3]:
            max_Udegree = max(max_Udegree, c.UDegree)
            max_Vdegree = max(max_Vdegree, c.VDegree)
        for c in [self.s1, self.s2, self.s3]:
            c.increaseDegree(max_Udegree, max_Vdegree)

        ad1 = SurfAdapterView(self.s1, 0)
        ad2 = SurfAdapterView(self.s2, 0)
        ad3 = SurfAdapterView(self.s3, 0)
        match_knots([ad1, ad2, ad3])
        ad1.d = 1
        ad2.d = 1
        ad3.d = 1
        match_knots([ad1, ad2, ad3])
        self.s1 = ad1.s
        self.s2 = ad2.s
        self.s3 = ad3.s

    def gordon(self):
        ns = self.s1.copy()
        for i in range(1, len(self.s1.getPoles()) + 1):
            for j in range(1, len(self.s1.getPoles()[0]) + 1):
                ns.setPole(i, j, self.s1.getPole(i, j) + self.s2.getPole(i, j) - self.s3.getPole(i, j))
        return ns

    @property
    def Surface(self):
        # self.input_surfaces_match()
        self.match_degrees_and_knots()
        return self.gordon()


class CurvesOn2Rails:
    """Surface defined by a series of curves on 2 rails"""
    def __init__(self, curves, rails):
        self.curves = curves
        self.rails = rails

    def build_surface(self):
        cts = CurvesToSurface(self.curves)
        s1 = cts.Surface
        s2 = _utils.ruled_surface(self.rails[0].toShape(), self.rails[1].toShape(), True).Surface
        s2.exchangeUV()
        s3 = U_linear_surface(s1)
        gordon = Gordon(s1, s2, s3)
        if gordon.input_surfaces_match():
            return gordon.Surface
        return gordon.Surface



