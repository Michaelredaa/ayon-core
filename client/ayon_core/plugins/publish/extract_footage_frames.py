"""
Requires:
    instance -> otioTrimmingRange
    instance -> representations

"""

import os
from copy import deepcopy

import pyblish.api

from ayon_core.lib import (
    get_ffmpeg_tool_args,
    run_subprocess,
)
from ayon_core.pipeline import publish


class ExtractMMFootage(publish.Extractor):
    """
    Trimming video file longer then required lenght

    """
    order = pyblish.api.ExtractorOrder
    label = "Extract Matchmove Footage"
    families = ["footage"]
    hosts = ["resolve", "hiero", "flame"]

    def process(self, instance):
        self.log.debug("self.staging_dir: {}".format(self.staging_dir))
        self.staging_dir = self.staging_dir(instance)
        otio_trim_range = instance.data["otioTrimmingRange"]
        representations = instance.data["representations"]
        versionData = instance.data["versionData"]
        fps = versionData.get("fps")
        self.log.debug("otio_trim_range: {}".format(otio_trim_range))
        self.log.debug("self.staging_dir: {}".format(self.staging_dir))

        # get corresponding representation
        for _repre in representations:
            if "footage" not in _repre["tags"]:
                continue
            
            self.log.debug("_repre: {}".format(_repre))
            
            input_file = _repre["file"]
            input_file_path = os.path.normpath(os.path.join(
                _repre["stagingDir"], input_file
            ))
            self.log.debug("input_file_path: {}".format(input_file_path))
            frame_start = _repre.get("frameStart")
            frame_end = _repre.get("frameEnd")
            self.log.info(
            "frame_start-frame_end: {}-{}".format(frame_start, frame_end))
            ext = _repre.get("ext", "jpg")
            self.log.debug("ext: {}".format(ext))
            # trim via ffmpeg
            new_files = self._ffmpeg_write_frames(
                input_file_path, ext, otio_trim_range, frame_start, frame_end, fps=fps)

            # prepare new representation data
            repre_data = deepcopy(_repre)
            # remove tags as we dont need them
            repre_data["stagingDir"] = self.staging_dir
            repre_data["files"] = new_files

            # romove `trim` tagged representation
            representations.remove(_repre)
            representations.append(repre_data)
            self.log.debug(repre_data)

        self.log.debug("representations: {}".format(representations))

    def _ffmpeg_write_frames(self, input_file_path, ext, otio_range, frame_start, frame_end, fps):
        """
        Trim seqment of video file.

        Using ffmpeg to trim video to desired length.

        Args:
            input_file_path (str): path string
            otio_range (opentime.TimeRange): range to trim to

        """
        # create path to destination
        output_path = self._get_ffmpeg_output(input_file_path, ext)

        # start command list
        command = get_ffmpeg_tool_args("ffmpeg")

        video_path = input_file_path
        sec_start = otio_range.start_time.to_seconds()
        sec_duration = otio_range.duration.to_seconds()
        
        self.log.debug("Duration: {} -> {}".format(sec_start, sec_duration))
    

        # form command for rendering gap files
        command.extend([
            "-ss", str(sec_start),
            "-t", str(sec_duration),
            "-r", str(int(fps)),
            "-i", video_path,
            "-q:v", "2",
            "-start_number", str(frame_start),
            output_path
        ])

        # execute
        self.log.debug("Executing: {}".format(" ".join(command)))
        output = run_subprocess(
            command, logger=self.log
        )
        self.log.debug("Output: {}".format(output))
        return [
            os.path.basename(output_path).replace("%04d", "{:04d}".format(i))
            for i in range(frame_start, frame_end + 1)
            ]

    def _get_ffmpeg_output(self, file_path, ext):
        """
        Returning ffmpeg output command arguments.

        Arguments"
            file_path (str): path string

        Returns:
            str: output_path is path

        """
        basename = os.path.basename(file_path)
        name, _ = os.path.splitext(basename)

        output_file = "{}.{}{}".format(
            name,
            "%04d.",
            ext
        )
        # create path to destination
        return os.path.join(self.staging_dir, output_file)
