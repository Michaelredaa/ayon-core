from pyblish import api
from ayon_core.settings import get_current_project_settings
import json


DEFAULT_TASKS = ["compositing"]
class CollectShotsDefaultTasks(api.InstancePlugin):
    """Collect Shots Default Tasks from project settings."""

    order = api.CollectorOrder - 0.076
    label = "Collect Shots Default Tasks"
    hosts = ["hiero", "resolve"]
    families = ["shot"]

    def process(self, instance):
        if "tasks" not in instance.data:
            instance.data["tasks"] = {}
            
        for task in self.get_default_tasks():
            instance.data["tasks"].update({
                task: {"type": task.capitalize()}
            })

        self.log.info("Collected Tasks: `{}`".format(
            instance.data["tasks"]))

    def get_default_tasks(self):
        settings = get_current_project_settings()
        core_settings = settings["core"]
        for filter in core_settings.get("filter_env_profiles", []):
            if "default_conform_tasks" in filter.get("host_names", []):
                return filter.get("task_names", []) or DEFAULT_TASKS
                    
        return DEFAULT_TASKS