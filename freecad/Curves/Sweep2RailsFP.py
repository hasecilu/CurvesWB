# -*- coding: utf-8 -*-

__title__ = 'Sweep 2 Rails'
__author__ = 'Christophe Grellier (Chris_G)'
__license__ = 'LGPL 2.1'
__doc__ = 'Create a sweep surface between two rails'

import os
import FreeCAD
import FreeCADGui
import Part
from freecad.Curves import curves_to_surface
from freecad.Curves import ICONPATH

TOOL_ICON = os.path.join(ICONPATH, 'sweep2rails.svg')
# debug = _utils.debug
# debug = _utils.doNothing

props = """
App::PropertyBool
App::PropertyBoolList
App::PropertyFloat
App::PropertyFloatList
App::PropertyFloatConstraint
App::PropertyQuantity
App::PropertyQuantityConstraint
App::PropertyAngle
App::PropertyDistance
App::PropertyLength
App::PropertySpeed
App::PropertyAcceleration
App::PropertyForce
App::PropertyPressure
App::PropertyInteger
App::PropertyIntegerConstraint
App::PropertyPercent
App::PropertyEnumeration
App::PropertyIntegerList
App::PropertyIntegerSet
App::PropertyMap
App::PropertyString
App::PropertyUUID
App::PropertyFont
App::PropertyStringList
App::PropertyLink
App::PropertyLinkSub
App::PropertyLinkList
App::PropertyLinkSubList
App::PropertyMatrix
App::PropertyVector
App::PropertyVectorList
App::PropertyPlacement
App::PropertyPlacementLink
App::PropertyColor
App::PropertyColorList
App::PropertyMaterial
App::PropertyPath
App::PropertyFile
App::PropertyFileIncluded
App::PropertyPythonObject
Part::PropertyPartShape
Part::PropertyGeometryList
Part::PropertyShapeHistory
Part::PropertyFilletEdges
Sketcher::PropertyConstraintList
"""


class Sweep2RailsObjProxy:
    "Proxy of the Sweep 2 Rails Feature"

    def __init__(self, obj, sel):
        """Add the properties"""
        obj.addProperty("App::PropertyLinkList", "Rails",
                        "Sources", "Tooltip")
        obj.addProperty("App::PropertyLinkList", "Profiles",
                        "Sources", "Tooltip")
        obj.Rails = sel[:2]
        obj.Profiles = sel[2:]
        obj.Proxy = self

    def get_curves(self, linklist):
        curves = []
        for link in linklist:
            e = link.Shape.Edge1
            c = e.Curve.toBSpline(e.FirstParameter, e.LastParameter)
            # c = e.Curve
            # c.trim(e.FirstParameter, e.LastParameter)
            curves.append(c)
        return curves

    def execute(self, obj):
        rails = self.get_curves(obj.Rails)
        profiles = self.get_curves(obj.Profiles)
        s2r = curves_to_surface.CurvesOn2Rails(profiles, rails)
        s = s2r.build_surface()
        obj.Shape = s.toShape()

    def onChanged(self, obj, prop):
        pass


class Sweep2RailsViewProxy:
    def __init__(self, viewobj):
        viewobj.Proxy = self

    def getIcon(self):
        return TOOL_ICON

    def attach(self, viewobj):
        self.Object = viewobj.Object

    def __getstate__(self):
        return {"name": self.Object.Name}

    def __setstate__(self, state):
        self.Object = FreeCAD.ActiveDocument.getObject(state["name"])
        return None


class Sweep2RailsCommand:
    "The Sweep 2 Rails feature creation command"

    def makeFeature(self, sel=None):
        fp = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Sweep 2 Rails")
        Sweep2RailsObjProxy(fp, sel)
        Sweep2RailsViewProxy(fp.ViewObject)
        FreeCAD.ActiveDocument.recompute()

    def Activated(self):
        sel = FreeCADGui.Selection.getSelection()
        if len(sel) < 1:
            FreeCAD.Console.PrintError("Select 2 rails and at least 2 profiles\n")
        else:
            self.makeFeature(sel)

    def IsActive(self):
        if FreeCAD.ActiveDocument:
            return True
        else:
            return False

    def GetResources(self):
        return {'Pixmap': TOOL_ICON,
                'MenuText': __title__,
                'ToolTip': __doc__}


FreeCADGui.addCommand('Curves_Sweep2Rails', Sweep2RailsCommand())