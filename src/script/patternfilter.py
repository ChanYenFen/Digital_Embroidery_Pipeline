__author__ = "Yen-Fen Chan"
__date__ = "2024.04.22"
__update__ = "2025.12.01"

import Rhino.Geometry as rg
import ghpythonlib.treehelpers as th
import random

class PatternFilter():
    DIST_MIN = 1.0

    def __init__(self,pts, width, p_width):
        self.pts = pts
        self.width = width
        self.p_width = p_width

    def check_length(self,lst):
        if len(lst) != 2:
            raise ValueError("List must have a length of 2.")

    def two_points_direction(self, pts):
        self.check_length(pts)
        dir_vector = pts[1] - pts[0]
        dir_vector.Unitize()
        return dir_vector

    def random_boolean(self):
        return random.choice([True, False])

    def zigzag(self):
        output_pts = []
        num_pts = len(self.pts)

        if num_pts < 2:
            return output_pts

        for j in range(num_pts - 1):
            pt_start = self.pts[j]
            pt_end = self.pts[j + 1]

            # Use the helper method
            dir_vector = self.two_points_direction([pt_start, pt_end])
            dist = pt_start.DistanceTo(pt_end)

            # Compute alternating normal vector
            normal_vector = rg.Vector3d.CrossProduct(dir_vector, rg.Vector3d.ZAxis)
            if j % 2 != 0:
                normal_vector.Reverse()

            # Midpoint offset
            translation = (dir_vector * (dist * 0.5)) + (normal_vector * self.width)
            mid_point = pt_start + translation

            output_pts.append(mid_point)

        return output_pts
    
    def cross(self):
        output_pts = []
        pts_1 = []
        pts_2 = []

        num_pts = len(self.pts)
        if num_pts < 2:
            return output_pts

        for j in range(num_pts - 1):
            pt_start = self.pts[j]
            pt_end = self.pts[j + 1]

            dir_vector = self.two_points_direction([pt_start, pt_end])
            dist = pt_start.DistanceTo(pt_end)

            normal_vector = rg.Vector3d.CrossProduct(dir_vector, rg.Vector3d.ZAxis)
            if j % 2 != 0:
                normal_vector.Reverse()

            # First side
            pts_1.append(pt_start + (normal_vector * (self.width * 0.5)))
            pts_1.append(pt_start + (dir_vector * (dist * 0.5)))
            pts_1.append(pt_start + (dir_vector * dist) + (normal_vector * (-self.width * 0.5)))

            # Second side
            pts_2.append(pt_start + (normal_vector * (-self.width * 0.5)))
            pts_2.append(pt_start + (dir_vector * (dist * 0.5)))
            pts_2.append(pt_start + (dir_vector * dist) + (normal_vector * (self.width * 0.5)))

        pts_2.reverse()
        output_pts.extend(pts_1 + pts_2)

        return output_pts

    def decorative(self, degree = 3, flip = False):
        output_pts = []
        for j, pt in enumerate(self.pts):
            seven_pts = []
            if j != len(self.pts) - 1:
                dir = self.two_points_direction([self.pts[j],self.pts[j+1]])
                # #hard coded here so pattern is always pointing up
                # if self.pts[j].X >self.pts[j+1].X:
                #     flip = True
                # #
                normal = rg.Vector3d.CrossProduct(dir, rg.Vector3d.ZAxis) if flip else rg.Vector3d.CrossProduct(dir, rg.Vector3d.ZAxis) * -1
                dist= pt.DistanceTo(self.pts[j+1])
                seven_pts.append(pt)
                T = dir*(dist-self.p_width)/2
                seven_pts.append(rg.Point3d.Add(pt,T))
                T = dir*dist + normal*self.width/2
                seven_pts.append(rg.Point3d.Add(pt,T))
                T = dir*dist/2 + normal*self.width
                seven_pts.append(rg.Point3d.Add(pt,T))
                T = normal*self.width/2
                seven_pts.append(rg.Point3d.Add(pt,T))
                T = dir*(dist/2+self.p_width/2)
                seven_pts.append(rg.Point3d.Add(pt,T))
                seven_pts.append(self.pts[j+1])
                crv = rg.Curve.CreateControlPointCurve(seven_pts,degree)
                count = int(crv.GetLength()/self.DIST_MIN)
                params = crv.DivideByCount(count,True)
                ppts = [crv.PointAt(p) for p in params]
                output_pts.extend(ppts)
        return output_pts
    
    def arrow(self):
        output_pts=[]
        for j,pt in enumerate(self.pts):
            if j!=len(self.pts)-1:
                dir = self.two_points_direction([self.pts[j],self.pts[j+1]])
                normal = rg.Vector3d.CrossProduct(dir, rg.Vector3d.ZAxis) if j%2==0 else rg.Vector3d.CrossProduct(dir, rg.Vector3d.ZAxis) * -1
                dist= pt.DistanceTo(self.pts[j+1])
                output_pts.append(pt.Clone())
                T =  (normal*self.width/2)
                output_pts.append(rg.Point3d.Add(pt,T))
                T = (dir*(dist-0.1))
                output_pts.append(rg.Point3d.Add(pt,T))
                T = (normal*self.width/-2)
                output_pts.append(rg.Point3d.Add(pt,T))
                output_pts.append(pt.Clone())          
        return output_pts

    def feather(self, flip = True, random_groth  =True):
        output_pts=[]
        for j, pt in enumerate(self.pts):
            output_pts.append(pt)
            if j!=len(self.pts)-1:
                dir = self.two_points_direction([self.pts[j], self.pts[j+1]])
                dist= pt.DistanceTo(self.pts[j+1])
                normal = rg.Vector3d.CrossProduct(dir, rg.Vector3d.ZAxis) if flip else rg.Vector3d.CrossProduct(dir, rg.Vector3d.ZAxis) * -1
                T = (dir*dist/2) + (normal*self.width/2)
                mid_pt = rg.Point3d.Add(pt,T)
                output_pts.append(mid_pt)
                if self.random_boolean():
                    T = mid_pt-self.pts[j+1]
                    output_pts.append(rg.Point3d.Add(mid_pt,T))
                    output_pts.append(mid_pt)
        return output_pts

if __name__ == "__main__":

    if do_pattern:

        patternPts_nested=[]
  
        for i, (pts, type, width) in enumerate(zip(pts_nested, pattern_sorted, width_sorted)):
            # print(i)

            myPa = PatternFilter(pts, width, 10.0)
            
            if type ==0:
                pattern_pts = pts
            elif type ==1:
                pattern_pts = myPa.zigzag()
            elif type ==2:
                pattern_pts = myPa.cross()
            elif type ==3:
                pattern_pts = myPa.decorative(flip=False)
            elif type ==4:
                pattern_pts = myPa.arrow()
            elif type ==5:
                pattern_pts = myPa.feather(flip=False,random_groth=True)
            patternPts_nested.append(pattern_pts)

    else:
        patternPts_nested = pts_nested

    vis = th.list_to_tree(patternPts_nested)
