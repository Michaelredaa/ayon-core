"""
Requires:
    instance -> otio_clip

Provides:
    instance -> otioReviewClips
"""

import os
import math

import pyblish.api
import clique

from ayon_core.pipeline import publish
from ayon_core.pipeline.publish import get_publish_template_name

EXT = "jpg"


class CollectMMFootage(
    pyblish.api.InstancePlugin,
    publish.ColormanagedPyblishPluginMixin
):
    """
    Collect Matchmove Footage for editorial shot.

    Handles in/out frames, creates representations, and prepares
    instance data for downstream publishing.
    """

    label = "Collect Matchmove Footage"
    order = pyblish.api.CollectorOrder + 0.492
    families = ["clip"]
    hosts = ["resolve", "hiero", "flame"]

    """
    Handle In      Clip In                    Clip Out      Handle Out
    |               |                          |             |
    |---------------|==========================|-------------|
    extra frames     actual shot frames
    """

    def process(self, instance):
        # Ensure instance belongs to footage family
        instance.data["families"].append("footage")

        # Local imports for hosts that may not have these modules globally
        import opentimelineio as otio
        from ayon_core.pipeline.editorial import (
            get_media_range_with_retimes,
            range_from_frames,
            make_sequence_collection
        )

        # Ensure representations and versionData exist
        instance.data.setdefault("representations", [])
        instance.data.setdefault("versionData", {})

        # Get anatomy template path for publishing
        template_name = self.get_template_name(instance)
        anatomy = instance.context.data["anatomy"]
        publish_path_template = anatomy.get_template_item(
            "publish", template_name, "path"
        ).template
        template = os.path.normpath(publish_path_template)
        self.log.debug(f">> template: {template}")

        handle_start = instance.data.get("handleStart", 0)
        handle_end = instance.data.get("handleEnd", 0)

        # Get OTIO clip and metadata
        otio_clip = instance.data["otioClip"]
        otio_available_range = otio_clip.available_range()
        media_fps = otio_available_range.start_time.rate
        available_duration = otio_available_range.duration.value

        # Apply retimes and trim attributes
        retimed_attributes = get_media_range_with_retimes(
            otio_clip, handle_start, handle_end
        )
        self.log.debug(f">> retimed_attributes: {retimed_attributes}")

        media_in = math.floor(retimed_attributes["mediaIn"])
        media_out = math.ceil(retimed_attributes["mediaOut"])
        handle_start = int(retimed_attributes["handleStart"])
        handle_end = int(retimed_attributes["handleEnd"])

        self.log.debug(f"media_in: {media_in}, media_out: {media_out}")
        self.log.debug(f"handle_start: {handle_start}, handle_end: {handle_end}")
        self.log.debug(f"available_duration: {available_duration}, media_fps: {media_fps}")

        # Update versionData if retime exists
        version_data = retimed_attributes.get("versionData")
        if version_data:
            instance.data["versionData"].update(version_data)

        # Calculate frame range including handles
        a_frame_start_h = media_in - handle_start
        a_frame_end_h = media_out + handle_end
        trimmed_media_range_h = range_from_frames(
            a_frame_start_h, (a_frame_end_h - a_frame_start_h) + 1, media_fps
        )
        trimmed_duration = trimmed_media_range_h.duration.value

        instance.data["otioTrimmingRange"] = trimmed_media_range_h

        self.log.debug(f"trimmed_media_range_h: {trimmed_media_range_h}")
        self.log.debug(f"a_frame_start_h: {a_frame_start_h}, a_frame_end_h: {a_frame_end_h}")

        # Set frame start/end for instance
        frame_start = instance.data["frameStart"]
        frame_end = frame_start + (media_out - media_in)

        fps = anatomy["attributes"]["fps"]
        instance.data["versionData"].update({
            "fps": fps,
            "frameStart": frame_start,
            "frameEnd": frame_end
        })

        # Get media reference and staging directory
        media_ref = otio_clip.media_reference
        metadata = media_ref.metadata
        dirname, filename = os.path.split(media_ref.target_url)
        self.staging_dir = dirname
        instance.data["originalDirname"] = self.staging_dir

        self.log.info(f"frame_start-frame_end: {frame_start}-{frame_end}")

        # Create representation and add to instance
        repre = self._create_representation(frame_start, frame_end, file=media_ref.target_url)
        if repre:
            instance.data["representations"].append(repre)

        self.log.debug(instance.data)

    def _create_representation(self, start, end, **kwargs):
        """
        Create a representation dictionary for the trimmed clip.

        Args:
            start (int): start frame
            end (int): end frame
            kwargs (dict): optional parameters (file path)

        Returns:
            dict: representation data
        """
        file = kwargs.get("file")
        return {
            "stagingDir": self.staging_dir,
            "name": EXT,
            "ext": EXT,
            "file": file,
            "frameStart": start,
            "frameEnd": end,
            "tags": ["footage", "plate"],
        }

    def get_template_name(self, instance):
        """
        Get anatomy template name for publishing integration.

        Args:
            instance: Pyblish instance

        Returns:
            str: template name
        """
        context = instance.context
        project_name = context.data["projectName"]
        host_name = context.data["hostName"]
        product_type = instance.data["productType"]
        anatomy_data = instance.data.get("anatomyData", {})
        task_info = anatomy_data.get("task", {})

        return get_publish_template_name(
            project_name,
            host_name,
            product_type,
            task_name=task_info.get("name"),
            task_type=task_info.get("type"),
            project_settings=context.data["project_settings"],
            logger=self.log
        )
