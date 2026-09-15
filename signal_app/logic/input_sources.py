"""
Input Source Abstraction Layer for Smart Adaptive Traffic Signal Control.

Provides a unified interface for feeding video frames into the AI processing pipeline,
whether from pre-recorded video files, in-memory image buffers (from browser webcam uploads),
or direct hardware camera feeds.
"""

from abc import ABC, abstractmethod
import cv2
import numpy as np
import os


class TrafficInputSource(ABC):
    """
    Abstract Base Class for all traffic video/frame input sources.
    The AI Detection and Tracking pipeline interacts ONLY with this interface.
    """

    @abstractmethod
    def get_frame(self):
        """
        Retrieve the next frame from the input source.
        Returns:
            tuple: (success: bool, frame: np.ndarray or None, frame_index: int or float)
        """
        pass

    @abstractmethod
    def get_total_frames(self):
        """Return total frames if known, or 0 for live streams."""
        pass

    @abstractmethod
    def get_fps(self):
        """Return frames per second of the source, or default 30.0."""
        pass

    @abstractmethod
    def release(self):
        """Release underlying system resources (video files, device handles)."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class VideoFileInputSource(TrafficInputSource):
    """
    Input source for pre-recorded video files (MP4, AVI, MOV, WebM, MKV).
    Supports frame resizing for high performance without losing aspect ratio.
    """

    def __init__(self, video_path, target_max_width=640):
        self.video_path = video_path
        self.target_max_width = target_max_width
        self.cap = cv2.VideoCapture(video_path)
        self.current_frame_idx = 0

        if not self.cap.isOpened():
            self._is_valid = False
            self.total_frames = 0
            self.fps = 30.0
            self.original_width = 0
            self.original_height = 0
        else:
            self._is_valid = True
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.original_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.original_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    @property
    def is_valid(self):
        return self._is_valid

    def get_frame(self):
        if not self._is_valid or self.cap is None:
            return False, None, self.current_frame_idx

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return False, None, self.current_frame_idx

        idx = self.current_frame_idx
        self.current_frame_idx += 1

        # Resize for performance if needed while preserving aspect ratio
        if self.target_max_width and frame.shape[1] > self.target_max_width:
            scale = self.target_max_width / float(frame.shape[1])
            new_h = int(frame.shape[0] * scale)
            frame = cv2.resize(frame, (self.target_max_width, new_h), interpolation=cv2.INTER_AREA)

        return True, frame, idx

    def get_total_frames(self):
        return self.total_frames

    def get_fps(self):
        return self.fps

    def seek_frame(self, frame_idx):
        """Seek to a specific frame position."""
        if self._is_valid and self.cap is not None:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            self.current_frame_idx = frame_idx

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            self._is_valid = False


class BufferFrameInputSource(TrafficInputSource):
    """
    Input source for single in-memory frame buffers (e.g. uploaded JPEG frames from browser camera).
    Decodes buffer into BGR numpy array.
    """

    def __init__(self, frame_bytes, target_max_width=640):
        self.target_max_width = target_max_width
        self.read_done = False

        if isinstance(frame_bytes, (bytes, bytearray)):
            nparr = np.frombuffer(frame_bytes, np.uint8)
            self.frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(frame_bytes, np.ndarray):
            self.frame = frame_bytes
        else:
            self.frame = None

        if self.frame is not None and self.target_max_width and self.frame.shape[1] > self.target_max_width:
            scale = self.target_max_width / float(self.frame.shape[1])
            new_h = int(self.frame.shape[0] * scale)
            self.frame = cv2.resize(self.frame, (self.target_max_width, new_h), interpolation=cv2.INTER_AREA)

    def get_frame(self):
        if not self.read_done and self.frame is not None:
            self.read_done = True
            return True, self.frame.copy(), 0
        return False, None, 1

    def get_total_frames(self):
        return 1

    def get_fps(self):
        return 1.0

    def release(self):
        self.frame = None
        self.read_done = True
