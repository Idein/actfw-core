from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from actfw_core.v4l2.types import bcm2835_isp_stats
from actfw_core.v4l2.video import VideoBuffer  # type: ignore


def clamp(x: float, low: float, high: float) -> float:
    return max(low, min(x, high))


PDAF_STATS_ROWS = 12
PDAF_STATS_COLS = 16
CONTRAST_STATS_ROWS = 3
CONTRAST_STATS_COLS = 4
MAX_WINDOWS = 10


class AfRange(Enum):
    AfRangeNormal = "normal"
    AfRangeMacro = "macro"
    AfRangeFull = "full"
    AfRangeMax = "max"


class AfSpeed(Enum):
    AfSpeedNormal = "normal"
    AfSpeedFast = "fast"
    AfSpeedMax = "max"


class AfMode(Enum):
    AfModeManual = 0
    AfModeAuto = 1
    AfModeContinuous = 2


class AfPause(Enum):
    AfPauseImmediate = 0
    AfPauseDeferred = 1
    AfPauseResume = 2


class AfState(Enum):
    Idle = 0
    Scanning = 1
    Focused = 2
    Failed = 3


class AfPauseState(Enum):
    Running = 0
    Pausing = 1
    Paused = 2


class AfStatus:
    def __init__(self) -> None:
        self.state: AfState = AfState.Idle
        self.pauseState: AfPauseState = AfPauseState.Running
        self.lensSetting: Optional[int] = None


class ScanState(Enum):
    Idle = 0
    Trigger = 1
    Pdaf = 2
    Coarse = 3
    Fine = 4
    Settle = 5


"""
Default values for parameters. All may be overridden in the tuning file.
any of these values are sensor- or module-dependent; the defaults here
assume IMX708 in a Raspberry Pi V3 camera with the standard lens.
"""


class RangeDependentParams:
    def __init__(self) -> None:
        self.focusMin = 0.0
        self.focusMax = 12.0
        self.focusDefault = 1.0

    def read(self, params: Dict[str, Any]) -> None:
        self.focusMin = params.get("min", self.focusMin)
        self.focusMax = params.get("max", self.focusMax)
        self.focusDefault = params.get("default", self.focusDefault)


class SpeedDependentParams:
    def __init__(self) -> None:
        self.stepCoarse = 1.0
        self.stepFine = 0.25
        self.contrastRatio = 0.75
        self.pdafGain = -0.02
        self.pdafSquelch = 0.125
        self.maxSlew = 2.0
        self.pdafFrames = 20
        self.dropoutFrames = 6
        self.stepFrames = 4

    def read(self, params: Dict[str, Any]) -> None:
        self.stepCoarse = params.get("step_coarse", self.stepCoarse)
        self.stepFine = params.get("step_fine", self.stepFine)
        self.contrastRatio = params.get("contrast_ratio", self.contrastRatio)
        self.pdafGain = params.get("pdaf_gain", self.pdafGain)
        self.pdafSquelch = params.get("pdaf_squelch", self.pdafSquelch)
        self.maxSlew = params.get("max_slew", self.maxSlew)
        self.pdafFrames = params.get("pdaf_frames", self.pdafFrames)
        self.dropoutFrames = params.get("dropout_frames", self.dropoutFrames)
        self.stepFrames = params.get("step_frames", self.stepFrames)


class Pwl:
    def __init__(self, points: List[float]) -> None:
        assert len(points) % 2 == 0
        self.points_ = [[points[i], points[i + 1]] for i in range(0, len(points), 2)]

    def findSpan(self, x: float, span: int) -> int:
        """
        Pwls are generally small, so linear search may well be faster than
        binary, though could review this if large Pwls start turning up.
        """
        lastSpan = len(self.points_) - 2

        # Ensure span is within valid range
        span = max(0, min(lastSpan, span))

        # Adjust span based on x
        # assuming point[0] is x value
        while span < lastSpan and x >= self.points_[span + 1][0]:
            span += 1
        while span != 0 and x < self.points_[span][0]:
            span -= 1

        return span

    def eval(self, x: float) -> float:
        # Evaluate the piecewise linear function
        index = self.findSpan(x, len(self.points_) // 2 - 1)

        return self.points_[index][1] + (x - self.points_[index][0]) * (self.points_[index + 1][1] - self.points_[index][1]) / (
            self.points_[index + 1][0] - self.points_[index][0]
        )

    def inverse_eval(self, y: int) -> Optional[float]:
        # Find the corresponding x for a given y
        for i in range(len(self.points_) - 1):
            y1, y2 = self.points_[i][1], self.points_[i + 1][1]
            if (y1 <= y <= y2) or (y2 <= y <= y1):
                # Linear interpolation to find x
                x1, x2 = self.points_[i][0], self.points_[i + 1][0]
                return x1 + (y - y1) * (x2 - x1) / (y2 - y1)
        return None


class CfgParams:
    def __init__(self, params: Dict[str, Any]) -> None:
        self.confEpsilon = 8
        self.confThresh = 16
        self.confClip = 512
        self.skipFrames = 5
        self.ranges = {
            AfRange.AfRangeNormal: RangeDependentParams(),
            AfRange.AfRangeMacro: RangeDependentParams(),
            AfRange.AfRangeFull: RangeDependentParams(),
        }
        self.speeds = {
            AfSpeed.AfSpeedNormal: SpeedDependentParams(),
            AfSpeed.AfSpeedFast: SpeedDependentParams(),
        }
        self.read(params)

    def read(self, params: Dict[str, Any]) -> None:
        if "ranges" in params:
            rr = params["ranges"]
            self.ranges[AfRange.AfRangeNormal].read(rr.get("normal", {}))
            self.ranges[AfRange.AfRangeMacro].read(rr.get("macro", {}))

            self.ranges[AfRange.AfRangeFull].focusMin = min(
                self.ranges[AfRange.AfRangeNormal].focusMin,
                self.ranges[AfRange.AfRangeMacro].focusMin,
            )
            self.ranges[AfRange.AfRangeFull].focusMax = max(
                self.ranges[AfRange.AfRangeNormal].focusMax,
                self.ranges[AfRange.AfRangeMacro].focusMax,
            )
            self.ranges[AfRange.AfRangeFull].focusDefault = self.ranges[AfRange.AfRangeNormal].focusDefault
            self.ranges[AfRange.AfRangeFull].read(rr.get("full", {}))

        if "speeds" in params:
            ss = params["speeds"]
            self.speeds[AfSpeed.AfSpeedNormal].read(ss.get("normal", {}))
            self.speeds[AfSpeed.AfSpeedFast].read(ss.get("fast", {}))

        self.confEpsilon = params.get("conf_epsilon", self.confEpsilon)
        self.confThresh = params.get("conf_thresh", self.confThresh)
        self.confClip = params.get("conf_clip", self.confClip)
        self.skipFrames = params.get("skip_frames", self.skipFrames)

        if "map" in params:
            self.map = Pwl(params["map"])
        else:
            # Default mapping from dioptres to hardware setting
            DefaultMapX0 = 0.0
            DefaultMapY0 = 445.0
            DefaultMapX1 = 15.0
            DefaultMapY1 = 925.0
            self.map = Pwl([DefaultMapX0, DefaultMapY0, DefaultMapX1, DefaultMapY1])


class Rectangle:
    def __init__(self, xpos: float, ypos: float, w: float, h: float) -> None:
        self.x = xpos
        self.y = ypos
        self.width = w
        self.height = h


class PdafData:
    def __init__(self, conf: int, phase: int) -> None:
        self.conf = conf
        self.phase = phase


class PdafRegions:
    def __init__(self, height: int, width: int) -> None:
        self.height = height
        self.width = width
        self.pdaf_grid = [[PdafData(0, 0) for _ in range(width)] for _ in range(height)]
        self.numRegions = height * width


class ScanRecord:
    def __init__(self, focus: float, contrast: float, phase: float, conf: float) -> None:
        self.focus = focus
        self.contrast = contrast
        self.phase = phase
        self.conf = conf


class RegionWeights:
    def __init__(self, rows: int, cols: int) -> None:
        self.rows = rows
        self.cols = cols
        self.sum = 0.0
        self.w = [0.0] * rows * cols


class AutoFocuserBase(metaclass=ABCMeta):
    """
    Autofocus control algorithm
    https://github.com/raspberrypi/libcamera/blob/v0.3.2%2Brpt20240927/src/ipa/rpi/controller/rpi/af.cpp
    """

    def __init__(
        self,
        afrange: AfRange = AfRange.AfRangeNormal,
        afspeed: AfSpeed = AfSpeed.AfSpeedNormal,
        afmode: AfMode = AfMode.AfModeContinuous,
    ) -> None:
        self.bitdepth = 10  # hardcode
        self.afrange = afrange
        self.afspeed = afspeed
        self.afmode = afmode
        self.pause_flag = False
        self.statsRegion = Rectangle(0, 0, 0, 0)
        self.windows: List[Rectangle] = []
        self.phaseWeights = RegionWeights(rows=PDAF_STATS_ROWS, cols=PDAF_STATS_COLS)
        self.contrastWeights = RegionWeights(rows=CONTRAST_STATS_ROWS, cols=CONTRAST_STATS_COLS)
        # self.scan_state = ScanState.Idle
        self.scan_state = ScanState.Trigger if afmode == AfMode.AfModeContinuous else ScanState.Idle
        self.initted = False
        self.ftarget = -1.0
        self.fsmooth = -1.0
        self.prev_contrast = 0.0
        self.skip_count = 0
        self.step_count = 0
        self.drop_count = 0
        self.scan_max_contrast = 0.0
        self.scan_min_contrast = 1e9
        self.scan_max_index = 0
        self.scan_data: List[ScanRecord] = []
        self.report_state = AfState.Idle
        self.afstatus = AfStatus()

    def __update_lens_position(self) -> None:
        if self.scan_state.value >= ScanState.Pdaf.value:
            self.ftarget = clamp(
                self.ftarget,
                self.cfg.ranges[self.afrange].focusMin,
                self.cfg.ranges[self.afrange].focusMax,
            )
        if self.initted:
            self.fsmooth = clamp(
                self.ftarget,
                self.fsmooth - self.cfg.speeds[self.afspeed].maxSlew,
                self.fsmooth + self.cfg.speeds[self.afspeed].maxSlew,
            )
        else:
            self.fsmooth = self.ftarget
            self.initted = True
            self.skip_count = self.cfg.skipFrames

    def __startAF(self) -> None:
        if self.cfg.speeds[self.afspeed].dropoutFrames > 0 and (
            self.afmode == AfMode.AfModeContinuous or self.cfg.speeds[self.afspeed].pdafFrames > 0
        ):
            if not self.initted:
                self.ftarget = self.cfg.ranges[self.afrange].focusDefault
                self.__update_lens_position()
            self.step_count = 0 if self.afmode == AfMode.AfModeContinuous else self.cfg.speeds[self.afspeed].pdafFrames
            self.scan_state = ScanState.Pdaf
            self.scan_data.clear()
            self.drop_count = 0
            self.report_state = AfState.Scanning
        else:
            self.__start_programmed_scan()

    def __start_programmed_scan(self) -> None:
        self.ftarget = self.cfg.ranges[self.afrange].focusMin
        self.__update_lens_position()
        self.scan_state = ScanState.Coarse
        self.scan_max_contrast = 0.0
        self.scan_min_contrast = 1e9
        self.scan_max_index = 0
        self.scan_data.clear()
        self.step_count = self.cfg.speeds[self.afspeed].stepFrames
        self.report_state = AfState.Scanning

    def __doPDAF(self, phase: float, conf: float) -> None:
        phase *= self.cfg.speeds[self.afspeed].pdafGain

        if self.afmode == AfMode.AfModeContinuous:
            phase *= conf / (conf + self.cfg.confEpsilon)
            if abs(phase) < self.cfg.speeds[self.afspeed].pdafSquelch:
                a = phase / self.cfg.speeds[self.afspeed].pdafSquelch
                phase *= a * a
        else:
            if self.step_count >= self.cfg.speeds[self.afspeed].stepFrames:
                if abs(phase) < self.cfg.speeds[self.afspeed].pdafSquelch:
                    self.step_count = self.cfg.speeds[self.afspeed].stepFrames
            else:
                phase *= self.step_count / self.cfg.speeds[self.afspeed].stepFrames
        if phase < -1 * self.cfg.speeds[self.afspeed].maxSlew:
            phase = -1 * self.cfg.speeds[self.afspeed].maxSlew
            if self.ftarget <= self.cfg.ranges[self.afrange].focusMin:
                self.report_state = AfState.Failed
            else:
                self.report_state = AfState.Scanning
        elif phase > self.cfg.speeds[self.afspeed].maxSlew:
            phase = self.cfg.speeds[self.afspeed].maxSlew
            if self.ftarget >= self.cfg.ranges[self.afrange].focusMax:
                self.report_state = AfState.Failed
            else:
                self.report_state = AfState.Scanning
        else:
            self.report_state = AfState.Focused
        self.ftarget = self.fsmooth + phase

    def __early_termination_byphase(self, phase: float) -> bool:
        if len(self.scan_data) > 0 and self.scan_data[-1].conf >= self.cfg.confEpsilon:
            oldFocus = self.scan_data[-1].focus
            oldPhase = self.scan_data[-1].phase
            if (self.ftarget - oldFocus) * (phase - oldPhase) > 0.0:
                param = phase / (phase - oldPhase)
                if -3.0 <= param and param <= 3.5:
                    self.ftarget += param * (oldFocus - self.ftarget)
                    return True
        return False

    def __find_peak(self, i: int) -> float:
        f = self.scan_data[i].focus
        if i > 0 and i + 1 < len(self.scan_data):
            dropLo = self.scan_data[i].contrast - self.scan_data[i - 1].contrast
            dropHi = self.scan_data[i].contrast - self.scan_data[i + 1].contrast
            if 0.0 <= dropLo and dropLo < dropHi:
                param = 0.3125 * (1.0 - dropLo / dropHi) * (1.6 - dropLo / dropHi)
                f += param * (self.scan_data[i - 1].focus - f)
            elif 0.0 <= dropHi and dropHi < dropLo:
                param = 0.3125 * (1.0 - dropHi / dropLo) * (1.6 - dropHi / dropLo)
                f += param * (self.scan_data[i + 1].focus - f)
        return f

    def __doScan(self, contrast: float, phase: float, conf: float) -> None:
        if len(self.scan_data) == 0 or contrast > self.scan_max_contrast:
            self.scan_max_contrast = contrast
            self.scan_max_index = len(self.scan_data)
        if contrast < self.scan_min_contrast:
            self.scan_min_contrast = contrast
        self.scan_data.append(ScanRecord(self.ftarget, contrast, phase, conf))

        if self.scan_state == ScanState.Coarse:
            if (
                self.ftarget >= self.cfg.ranges[self.afrange].focusMax
                or contrast < self.cfg.speeds[self.afspeed].contrastRatio * self.scan_max_contrast
            ):
                self.ftarget = min(
                    self.ftarget,
                    self.__find_peak(self.scan_max_index) + 2.0 * self.cfg.speeds[self.afspeed].stepFine,
                )
                self.scan_state = ScanState.Fine
                self.scan_data.clear()
            else:
                self.ftarget += self.cfg.speeds[self.afspeed].stepCoarse
        else:
            if (
                self.ftarget <= self.cfg.ranges[self.afrange].focusMin
                or len(self.scan_data) >= 5
                or contrast < self.cfg.speeds[self.afspeed].contrastRatio * self.scan_max_contrast
            ):
                self.ftarget = self.__find_peak(self.scan_max_index)
                self.scan_state = ScanState.Settle
            else:
                self.ftarget -= self.cfg.speeds[self.afspeed].stepFine

        self.step_count = 0 if self.ftarget == self.fsmooth else self.cfg.speeds[self.afspeed].stepFrames

    def __doAF(self, contrast: float, phase: float, conf: float) -> None:
        if self.skip_count > 0:
            self.skip_count -= 1
            return
        if self.scan_state == ScanState.Pdaf:
            if conf > (1.0 if self.drop_count != 0 else 0.25) * self.cfg.confEpsilon:
                self.__doPDAF(phase, conf)
                if self.step_count > 0:
                    self.step_count -= 1
                elif self.afmode != AfMode.AfModeContinuous:
                    self.scan_state = ScanState.Idle
                self.drop_count = 0
            elif self.drop_count + 1 == self.cfg.speeds[self.afspeed].dropoutFrames:
                self.drop_count += 1
                self.__start_programmed_scan()
        elif self.scan_state.value >= ScanState.Coarse.value and self.fsmooth == self.ftarget:
            if self.step_count > 0:
                self.step_count -= 1
            elif self.scan_state == ScanState.Settle:
                if (
                    self.prev_contrast >= self.cfg.speeds[self.afspeed].contrastRatio * self.scan_max_contrast
                    and self.scan_min_contrast <= self.cfg.speeds[self.afspeed].contrastRatio * self.scan_max_contrast
                ):
                    self.report_state = AfState.Focused
                else:
                    self.report_state = AfState.Failed
                if (
                    self.afmode == AfMode.AfModeContinuous
                    and (not self.pause_flag)
                    and self.cfg.speeds[self.afspeed].dropoutFrames > 0
                ):
                    self.scan_state = ScanState.Pdaf
                else:
                    self.scan_state = ScanState.Idle
                self.scan_data.clear()
            elif conf >= self.cfg.confEpsilon and self.__early_termination_byphase(phase):
                self.scan_state = ScanState.Settle
                self.step_count = 0 if self.afmode == AfMode.AfModeContinuous else self.cfg.speeds[self.afspeed].stepFrames
            else:
                self.__doScan(contrast, phase, conf)

    def __compute_weights(self, weights: RegionWeights, rows: int, cols: int) -> None:
        weights.rows = rows
        weights.cols = cols
        weights.sum = 0
        weights.w = [0] * (rows * cols)
        if (
            rows > 0
            and cols > 0
            and len(self.windows) > 0
            and self.statsRegion.height >= rows
            and self.statsRegion.width >= cols
        ):
            maxCellWeight = 46080 // (MAX_WINDOWS * rows * cols)
            cellH = self.statsRegion.height // rows
            cellW = self.statsRegion.width // cols
            cellA = cellH * cellW
            for w in self.windows:
                for r in range(rows):
                    y0 = max(self.statsRegion.y + int(cellH * r), w.y)
                    y1 = min(self.statsRegion.y + int(cellH * (r + 1)), w.y + int(w.height))
                    if y0 >= y1:
                        continue
                    y1 -= y0
                    for c in range(cols):
                        x0 = max(self.statsRegion.x + int(cellW * c), w.x)
                        x1 = min(self.statsRegion.x + int(cellW * (c + 1)), w.x + int(w.width))
                        if x0 >= x1:
                            continue
                        a: float = y1 * (x1 - x0)
                        a = (maxCellWeight * a + cellA - 1) / cellA
                        weights.w[r * cols + c] += a
                        weights.sum += a
        if weights.sum == 0:
            for r in range(rows // 3, rows - rows // 3):
                for c in range(cols // 4, cols - cols // 4):
                    weights.w[r * cols + c] = 1
                    weights.sum += 1

    def __invalidate_weights(self) -> None:
        self.phaseWeights.sum = 0
        self.contrastWeights.sum = 0

    def __get_phase(self, regions: PdafRegions) -> Tuple[float, float, bool]:
        if regions.height != self.phaseWeights.rows or regions.width != self.phaseWeights.cols or self.phaseWeights.sum == 0:
            self.__compute_weights(self.phaseWeights, regions.height, regions.width)

        sumWc = 0
        sumWcp = 0
        for i in range(regions.numRegions):
            w = self.phaseWeights.w[i]
            if w != 0:
                data = regions.pdaf_grid[i // PDAF_STATS_COLS][i % PDAF_STATS_COLS]
                c = data.conf
                if c >= self.cfg.confThresh:
                    if c > self.cfg.confClip:
                        c = self.cfg.confClip
                    c -= self.cfg.confThresh >> 2
                    sumWc += int(w * c)
                    c -= self.cfg.confThresh >> 2
                    sumWcp += int(w * c) * int(data.phase)

        if 0 < self.phaseWeights.sum and self.phaseWeights.sum <= sumWc:
            phase = sumWcp / sumWc
            conf = sumWc / self.phaseWeights.sum
            return phase, conf, True
        else:
            return 0, 0, False

    def __prepare(self, regions: Optional[PdafRegions]) -> None:
        if self.scan_state == ScanState.Trigger:
            self.__startAF()

        if self.initted:
            phase = 0.0
            conf = 0.0
            if regions is not None:
                phase, conf, _ = self.__get_phase(regions)
            self.__doAF(self.prev_contrast, phase, conf)
            self.__update_lens_position()

        if self.pause_flag:
            self.afstatus.pauseState = AfPauseState.Paused if self.scan_state == ScanState.Idle else AfPauseState.Pausing
        else:
            self.afstatus.pauseState = AfPauseState.Running

        if self.afmode == AfMode.AfModeAuto and self.scan_state != ScanState.Idle:
            self.afstatus.state = AfState.Scanning
        else:
            self.afstatus.state = self.report_state
        lensSetting = self.cfg.map.eval(self.fsmooth)
        self.afstatus.lensSetting = int(lensSetting) if self.initted and lensSetting is not None else None
        try:
            if self.afstatus.lensSetting is not None:
                self.callback_fn(self.afstatus.lensSetting)
        except Exception:
            # Occasionally, the execution may fail due to the current state of the device.
            raise RuntimeWarning("Failed to execute the callback function")

    def __get_contrast(self, stats: bcm2835_isp_stats) -> float:
        if self.contrastWeights.sum == 0:
            self.__compute_weights(self.contrastWeights, CONTRAST_STATS_ROWS, CONTRAST_STATS_COLS)
        sumWc = 0
        for i in range(CONTRAST_STATS_ROWS * CONTRAST_STATS_COLS):
            # https://github.com/raspberrypi/libcamera/blob/v0.3.2%2Brpt20240927/src/ipa/rpi/vc4/vc4.cpp#L245
            val = stats.focus_stats[i].contrast_val[1][1] / 1000
            sumWc += self.contrastWeights.w[i] * val
        return sumWc / self.contrastWeights.sum if self.contrastWeights.sum > 0 else 0.0

    def set_unicam_config(
        self,
        sensor_config: Dict,
        unicam_width: int,
        sensor_size: Tuple[int, int],
        post_crop_size: Tuple[int, int, int, int],
        camera_mode_scale: Tuple[float, float],
        camera_mode_crop_size: Tuple[int, int],
        callback_fn: Callable,
    ) -> None:
        """
        This method is called in UnicamIspCapture.__init__().
        """
        if "rpi.af" not in sensor_config:
            raise RuntimeError("rpi.af is not found in sensor config")
        self.cfg = CfgParams(sensor_config["rpi.af"])
        self.line_width = unicam_width
        self.bytes_per_line = (self.line_width * self.bitdepth) >> 3
        self.callback_fn = callback_fn
        self.statsRegion = Rectangle(
            camera_mode_crop_size[0],
            camera_mode_crop_size[1],
            sensor_size[0] - 2 * camera_mode_crop_size[0],
            sensor_size[1] - 2 * camera_mode_crop_size[0],
        )
        # for window coordinate decode
        self.post_crop_size = post_crop_size
        self.camera_mode_scale = camera_mode_scale
        self.camera_mode_crop = camera_mode_crop_size

    def set_focus_windows(self, bboxes: List[List[float]]) -> None:
        """
        Configures the focus windows.
        bboxes: [[x1, y1, x2, y2], ...] defined in capture image coordinate system.
        """
        self.windows.clear()
        for bbox in bboxes[:MAX_WINDOWS]:
            x1, y1, x2, y2 = bbox
            self.windows.append(
                # Transform capture image coordinates to the sensor's coordinate system
                Rectangle(
                    (x1 + self.post_crop_size[0]) * self.camera_mode_scale[0] + self.camera_mode_crop[0],
                    (y1 + self.post_crop_size[1]) * self.camera_mode_scale[1] + self.camera_mode_crop[1],
                    (x2 - x1) * self.camera_mode_scale[0],
                    (y2 - y1) * self.camera_mode_scale[1],
                )
            )
        self.__invalidate_weights()

    def set_focus_value(self, value: int) -> None:
        if self.afmode == AfMode.AfModeManual:
            ftarget = self.cfg.map.inverse_eval(value)
            if ftarget is not None:
                self.afstatus.lensSetting = value
                self.ftarget = ftarget
                self.__update_lens_position()
                self.callback_fn(value)

    def get_focus_value(self) -> Optional[int]:
        """
        Return latest focus value.
        """
        return self.afstatus.lensSetting

    def get_focus_stats(self) -> AfStatus:
        """
        Return latest focus status.
        """
        return self.afstatus

    def trigger_scan(self) -> None:
        if self.afmode == AfMode.AfModeAuto and self.scan_state == ScanState.Idle:
            self.scan_state = ScanState.Trigger

    def process_contrast_metadata(self, stats: bcm2835_isp_stats) -> None:
        """
        Extract contrast information from the metadata received from the ISP device and store it for later use.
        """
        self.prev_contrast = self.__get_contrast(stats)

    @abstractmethod
    def parse_pdaf(self, meta_buffer: VideoBuffer) -> PdafRegions:
        raise NotImplementedError()

    def parse_pdaf_and_update_focus(self, meta_buffer: VideoBuffer) -> None:
        """
        Parse PDAF data from embedded metadata from the unicam meta device.
        Calculate the optimal lens position based on the analyzed data, and execute the callback function.
        """
        if meta_buffer.buf.bytesused < self.bytes_per_line * 3:
            raise RuntimeError("Insufficient metadata size")
        pdaf = self.parse_pdaf(meta_buffer)
        self.__prepare(pdaf)


class AutoFocuserIMX708(AutoFocuserBase):
    def __init__(
        self,
        afrange: AfRange = AfRange.AfRangeNormal,
        afspeed: AfSpeed = AfSpeed.AfSpeedNormal,
        afmode: AfMode = AfMode.AfModeContinuous,
    ) -> None:
        super().__init__(afrange, afspeed, afmode)

    def parse_pdaf(self, meta_buffer: VideoBuffer) -> PdafRegions:
        # https://github.com/raspberrypi/libcamera/blob/v0.3.2%2Brpt20240927/src/ipa/rpi/cam_helper/cam_helper_imx708.cpp#L267-L293
        bpp = 10  # hardcode
        pdaf = PdafRegions(height=PDAF_STATS_ROWS, width=PDAF_STATS_COLS)
        ptr = meta_buffer.mapped_buf[2 * self.bytes_per_line : 3 * self.bytes_per_line]
        step = bpp >> 1

        if bpp < 10 or bpp > 14 or self.bytes_per_line < 194 * step or ptr[0] != 0 or ptr[1] >= 0x40:
            raise RuntimeError("PDAF data in unsupported format")

        offset = 2 * step
        for i in range(PDAF_STATS_ROWS):
            for j in range(PDAF_STATS_COLS):
                conf = (ptr[offset] << 3) | (ptr[offset + 1] >> 5)
                phase = 0
                if conf != 0:
                    phase = (((ptr[offset + 1] & 0x0F) - (ptr[offset + 1] & 0x10)) << 6) | (ptr[offset + 2] >> 2)
                pdaf.pdaf_grid[i][j] = PdafData(conf, phase)
                offset += step
        return pdaf
