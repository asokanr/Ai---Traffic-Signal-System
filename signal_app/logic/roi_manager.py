"""
Normalized Region of Interest (ROI) and Lane Assignment Manager.

Provides resolution-independent, deterministic lane/direction assignment for detected vehicles.
Coordinates are defined in normalized range [0.0, 1.0] relative to frame width and height.
"""

import cv2
import numpy as np


class ROIManager:
    """
    Manages 4-direction traffic zones (North, South, East, West) using normalized polygons.
    """

    # Direction metadata
    DIRECTIONS = ['N', 'S', 'E', 'W']
    DIRECTION_NAMES = {
        'N': 'North',
        'S': 'South',
        'E': 'East',
        'W': 'West',
    }

    # Visual colors for each lane ROI (BGR format)
    DIRECTION_COLORS = {
        'N': (255, 180, 50),   # Cyan/Blue
        'S': (50, 150, 255),   # Orange/Amber
        'E': (80, 220, 80),    # Bright Green
        'W': (200, 80, 200),   # Purple/Magenta
    }

    def __init__(self, custom_rois=None, layout_type='4_way_intersection'):
        """
        Initialize ROI configurations.
        Args:
            custom_rois: Optional dict mapping 'N', 'S', 'E', 'W' to list of (norm_x, norm_y) points.
            layout_type: '4_way_intersection' (default), '4_lane_parallel', or 'quadrants'
        """
        self.layout_type = layout_type
        if custom_rois:
            self.rois = custom_rois
        else:
            self.rois = self._default_rois(layout_type)

    def _default_rois(self, layout_type):
        """
        Generate standard normalized 4-direction polygons.
        Coordinates: (x/width, y/height) in range 0.0 to 1.0.
        """
        if layout_type == '4_lane_parallel':
            # 4 parallel vertical lanes (e.g. 4-lane highway/expressway)
            return {
                'N': [(0.00, 0.00), (0.25, 0.00), (0.25, 1.00), (0.00, 1.00)],
                'S': [(0.25, 0.00), (0.50, 0.00), (0.50, 1.00), (0.25, 1.00)],
                'E': [(0.50, 0.00), (0.75, 0.00), (0.75, 1.00), (0.50, 1.00)],
                'W': [(0.75, 0.00), (1.00, 0.00), (1.00, 1.00), (0.75, 1.00)],
            }
        elif layout_type == 'quadrants':
            # 4 quadrant split
            return {
                'N': [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)],
                'E': [(0.5, 0.0), (1.0, 0.0), (1.0, 0.5), (0.5, 0.5)],
                'W': [(0.0, 0.5), (0.5, 0.5), (0.5, 1.0), (0.0, 1.0)],
                'S': [(0.5, 0.5), (1.0, 0.5), (1.0, 1.0), (0.5, 1.0)],
            }
        else:
            # Standard 4-way intersection approaches (top, bottom, right, left)
            return {
                'N': [(0.36, 0.00), (0.64, 0.00), (0.60, 0.40), (0.40, 0.40)],
                'S': [(0.38, 1.00), (0.62, 1.00), (0.60, 0.60), (0.40, 0.60)],
                'E': [(1.00, 0.20), (1.00, 0.48), (0.60, 0.48), (0.60, 0.30)],
                'W': [(0.00, 0.35), (0.00, 0.66), (0.40, 0.66), (0.40, 0.35)],
            }

    def get_pixel_polygon(self, direction, width, height):
        """Convert normalized polygon coordinates to pixel integer array."""
        norm_pts = self.rois.get(direction, [])
        if not norm_pts:
            return np.array([], dtype=np.int32)
        pts = [[int(x * width), int(y * height)] for (x, y) in norm_pts]
        return np.array(pts, dtype=np.int32)

    def assign_direction(self, cx, cy, width, height):
        """
        Deterministically assign a vehicle center point (cx, cy) to a direction (N, S, E, W).
        Returns:
            str: Direction code ('N', 'S', 'E', or 'W')
        """
        # 1. First check if the center point is strictly inside any configured ROI polygon
        for d in self.DIRECTIONS:
            pts = self.get_pixel_polygon(d, width, height)
            if len(pts) >= 3:
                # cv2.pointPolygonTest returns >= 0 if inside or on edge
                dist = cv2.pointPolygonTest(pts, (float(cx), float(cy)), False)
                if dist >= 0:
                    return d

        # 2. Deterministic Fallback: Nearest quadrant angle relative to frame center
        # Ensures no vehicle is lost or assigned randomly
        mid_x = width / 2.0
        mid_y = height / 2.0
        dx = cx - mid_x
        dy = cy - mid_y

        # Angle in degrees from center
        angle = np.degrees(np.arctan2(dy, dx))  # -180 to 180
        # -45 to 45: East
        # 45 to 135: South
        # -135 to -45: North
        # else: West
        if -45.0 <= angle < 45.0:
            return 'E'
        elif 45.0 <= angle < 135.0:
            return 'S'
        elif -135.0 <= angle < -45.0:
            return 'N'
        else:
            return 'W'

    def draw_rois(self, frame, lane_counts=None, active_direction=None, alpha=0.18):
        """
        Draw visual semi-transparent ROI polygons and lane tags on the frame.
        """
        h, w = frame.shape[:2]
        overlay = frame.copy()

        for d in self.DIRECTIONS:
            pts = self.get_pixel_polygon(d, w, h)
            if len(pts) < 3:
                continue

            color = self.DIRECTION_COLORS.get(d, (255, 255, 255))
            is_active = (d == active_direction)
            fill_color = (0, 255, 0) if is_active else color

            # Fill polygon
            cv2.fillPoly(overlay, [pts], fill_color)

            # Draw polygon border
            thickness = 3 if is_active else 1
            cv2.polylines(frame, [pts], True, color, thickness)

            # Draw direction & count label at the centroid of the ROI
            moments = cv2.moments(pts)
            if moments["m00"] != 0:
                mc_x = int(moments["m10"] / moments["m00"])
                mc_y = int(moments["m01"] / moments["m00"])
            else:
                mc_x, mc_y = pts[0][0], pts[0][1]

            cnt_text = f"{self.DIRECTION_NAMES[d]}: {lane_counts.get(d, 0)}" if lane_counts else self.DIRECTION_NAMES[d]
            (tw, th), _ = cv2.getTextSize(cnt_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(frame, (mc_x - tw // 2 - 4, mc_y - th // 2 - 4),
                          (mc_x + tw // 2 + 4, mc_y + th // 2 + 4), (15, 20, 30), -1)
            cv2.rectangle(frame, (mc_x - tw // 2 - 4, mc_y - th // 2 - 4),
                          (mc_x + tw // 2 + 4, mc_y + th // 2 + 4), color, 1)
            cv2.putText(frame, cnt_text, (mc_x - tw // 2, mc_y + th // 2 - 1),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        # Blend semi-transparent fill
        cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)
        return frame

    def get_roi_config(self):
        """Return raw normalized ROI dictionary."""
        return {
            'layout_type': self.layout_type,
            'directions': {
                d: [{'x': round(pt[0], 3), 'y': round(pt[1], 3)} for pt in self.rois.get(d, [])]
                for d in self.DIRECTIONS
            }
        }
