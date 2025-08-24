"""
Requires:
    instance -> otioTrimmingRange
    instance -> representations
"""

import os
from copy import deepcopy

import pyblish.api
from ayon_core.lib import get_ffmpeg_tool_args, run_subprocess
from ayon_core.pipeline import publish


class ExtractMMFootage(publish.Extractor):
    """
    Export Matchmove Footage from video file using FFmpeg.
    """

    order = pyblish.api.ExtractorOrder
    label = "Extract Matchmove Footage"
    families = ["footage"]
    hosts = ["resolve", "hiero", "flame"]

    def process(self, instance):
        self.log.debug(f"Initial staging_dir: {self.staging_dir}")
        self.staging_dir = self.staging_dir(instance)

        otio_trim_range = instance.data["otioTrimmingRange"]
        representations = instance.data["representations"]
        version_data = instance.data.get("versionData", {})
        fps = version_data.get("fps")

        self.log.debug(f"otio_trim_range: {otio_trim_range}")
        self.log.debug(f"staging_dir: {self.staging_dir}")

        for repre in representations[:]:  # Copy of list to modify safely
            if "footage" not in repre.get("tags", []):
                continue

            self.log.debug(f"Processing representation: {repre}")

            input_file = repre["file"]
            input_file_path = os.path.normpath(
                os.path.join(repre["stagingDir"], input_file)
            )
            frame_start = repre.get("frameStart")
            frame_end = repre.get("frameEnd")
            ext = repre.get("ext", "jpg")

            self.log.info(f"Frame range: {frame_start}-{frame_end}")
            self.log.debug(f"Input file path: {input_file_path}, ext: {ext}")

            # Trim frames via FFmpeg
            new_files = self._ffmpeg_write_frames(
                input_file_path, ext, otio_trim_range, frame_start, frame_end, fps=fps
            )

            # Prepare new representation
            new_repre = deepcopy(repre)
            new_repre["stagingDir"] = self.staging_dir
            new_repre["files"] = new_files

            # Replace old representation
            representations.remove(repre)
            representations.append(new_repre)
            self.log.debug(f"New representation: {new_repre}")

        self.log.debug(f"Final representations: {representations}")

    def _ffmpeg_write_frames(self, input_file_path, ext, otio_range, frame_start, frame_end, fps):
        """
        Trim a segment of a video file using FFmpeg.

        Args:
            input_file_path (str): Full path to the input file.
            ext (str): File extension for output frames.
            otio_range (opentime.TimeRange): Range to trim to.
            frame_start (int): First frame number.
            frame_end (int): Last frame number.
            fps (float): Frames per second for output.

        Returns:
            list[str]: List of output frame file names.
        """
        output_path = self._get_ffmpeg_output(input_file_path, ext)
        command = get_ffmpeg_tool_args("ffmpeg")

        sec_start = otio_range.start_time.to_seconds()
        sec_duration = otio_range.duration.to_seconds()
        self.log.debug(f"Trimming duration: start={sec_start}s, duration={sec_duration}s")

        command.extend([
            "-ss", str(sec_start),
            "-t", str(sec_duration),
            "-r", str(int(fps)),
            "-i", input_file_path,
            "-q:v", "2",
            "-start_number", str(frame_start),
            output_path
        ])

        self.log.debug(f"Executing command: {' '.join(command)}")
        output = run_subprocess(command, logger=self.log)
        self.log.debug(f"FFmpeg output: {output}")

        return [
            os.path.basename(output_path).replace("%04d", f"{i:04d}")
            for i in range(frame_start, frame_end + 1)
        ]

    def _get_ffmpeg_output(self, file_path, ext):
        """
        Returns the FFmpeg output file template.

        Args:
            file_path (str): Input file path.
            ext (str): Extension for output frames.

        Returns:
            str: Output file path with frame number pattern.
        """
        basename = os.path.basename(file_path)
        name, _ = os.path.splitext(basename)
        output_file = f"{name}.%04d.{ext}"
        return os.path.join(self.staging_dir, output_file)
