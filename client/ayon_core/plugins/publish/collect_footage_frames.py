"""
Requires:
    instance -> otio_clip

Provides:
    instance -> otioReviewClips
"""
import os
import math

import clique
import pyblish.api

from ayon_core.pipeline import publish
from ayon_core.pipeline.publish import (
    get_publish_template_name
)

EXT = "jpg"

class CollectMMFootage(
    pyblish.api.InstancePlugin,
    publish.ColormanagedPyblishPluginMixin
):
    """Get Resources for a product version"""

    """
    Handle In      Clip In                    Clip Out      Handle Out
    |               |                          |             |
    |---------------|==========================|-------------|
    extra frames     actual shot frames

    """
    
    label = "Collect Matchmove Footage"
    order = pyblish.api.CollectorOrder + 0.492
    families = ["clip"]
    hosts = ["resolve", "hiero", "flame"]

    def process(self, instance):
        
        instance.data["families"].append("footage")
        
        # Not all hosts can import these modules.
        import opentimelineio as otio
        from ayon_core.pipeline.editorial import (
            get_media_range_with_retimes,
            range_from_frames,
            make_sequence_collection
        )

        if not instance.data.get("representations"):
            instance.data["representations"] = []

        if not instance.data.get("versionData"):
            instance.data["versionData"] = {}

        template_name = self.get_template_name(instance)
        anatomy = instance.context.data["anatomy"]
        publish_path_template = anatomy.get_template_item(
            "publish", template_name, "path"
        ).template
        template = os.path.normpath(publish_path_template)
        self.log.debug(
            ">> template: {}".format(template))

        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        # get basic variables
        otio_clip = instance.data["otioClip"]
        otio_available_range = otio_clip.available_range()
        media_fps = otio_available_range.start_time.rate
        available_duration = otio_available_range.duration.value

        # get available range trimmed with processed retimes
        retimed_attributes = get_media_range_with_retimes(
            otio_clip, handle_start, handle_end)
        self.log.debug(
            ">> retimed_attributes: {}".format(retimed_attributes))


        media_in = math.floor(retimed_attributes["mediaIn"])
        media_out = math.ceil(retimed_attributes["mediaOut"])

        handle_start = int(retimed_attributes["handleStart"])
        handle_end = int(retimed_attributes["handleEnd"])
        
        
        self.log.debug("media_in: {}".format(media_in))
        self.log.debug("media_out: {}".format(media_out))   
        self.log.debug("handle_start: {}".format(handle_start))
        self.log.debug("handle_end: {}".format(handle_end))
        self.log.debug("available_duration: {}".format(available_duration))
        self.log.debug("media_fps: {}".format(media_fps))
        
        
        # set versiondata if any retime
        version_data = retimed_attributes.get("versionData")

        if version_data:
            instance.data["versionData"].update(version_data)

        # convert to available frame range with handles
        a_frame_start_h = media_in - handle_start
        a_frame_end_h = media_out + handle_end

        # create trimmed otio time range
        trimmed_media_range_h = range_from_frames(
            a_frame_start_h, (a_frame_end_h - a_frame_start_h) + 1,
            media_fps
        )
        trimmed_duration = trimmed_media_range_h.duration.value

        self.log.debug("trimmed_media_range_h: {}".format(
            trimmed_media_range_h))
        self.log.debug("a_frame_start_h: {}".format(
            a_frame_start_h))
        self.log.debug("a_frame_end_h: {}".format(
            a_frame_end_h))

        # create frame start and end
        frame_start = instance.data["frameStart"]
        frame_end = frame_start + (media_out - media_in)
            
        fps = anatomy["attributes"]["fps"]
        self.log.debug("Anatomy attributes: {}".format(anatomy.items()))
        # add to version data start and end range data
        # for loader plugins to be correctly displayed and loaded
        instance.data["versionData"].update({
            "fps": fps
        })

        instance.data["versionData"].update({
            "frameStart": frame_start,
            "frameEnd": frame_end
        })

        # change frame_start and frame_end values
        # for representation to be correctly renumbered in integrate_new
        # frame_start -= handle_start
        # frame_end += handle_end

        media_ref = otio_clip.media_reference
        metadata = media_ref.metadata

        self.log.info(
            "frame_start-frame_end: {}-{}".format(frame_start, frame_end))

        dirname, filename = os.path.split(media_ref.target_url)
        self.staging_dir = dirname
            
        self.log.debug(filename)
        repre = self._create_representation(
            frame_start, frame_end, file=media_ref.target_url)


        instance.data["originalDirname"] = self.staging_dir

        # add representation to instance data
        if repre:
            colorspace = instance.data.get("colorspace")
            # add colorspace data to representation
            # self.set_representation_colorspace(
            #     repre, instance.context, colorspace)

            instance.data["representations"].append(repre)

        self.log.debug(instance.data)

    def _create_representation(self, start, end, **kwargs):
        """
        Creating representation data.

        Args:
            start (int): start frame
            end (int): end frame
            kwargs (dict): optional data

        Returns:
            dict: representation data
        """

        file = kwargs.get("file")
        representation_data ={
            "stagingDir": self.staging_dir,
            "name": EXT,
            "ext": EXT,
            "file": file,
            "frameStart": start,
            "frameEnd": end,
            "tags": ["footage", "plate"],
        }
        return representation_data

    def get_template_name(self, instance):
        """Return anatomy template name to use for integration"""

        # Anatomy data is pre-filled by Collectors
        context = instance.context
        project_name = context.data["projectName"]

        # Task can be optional in anatomy data
        host_name = context.data["hostName"]
        product_type = instance.data["productType"]
        anatomy_data = instance.data["anatomyData"]
        task_info = anatomy_data.get("task") or {}

        return get_publish_template_name(
            project_name,
            host_name,
            product_type,
            task_name=task_info.get("name"),
            task_type=task_info.get("type"),
            project_settings=context.data["project_settings"],
            logger=self.log
        )
