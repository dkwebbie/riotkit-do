
import os
from typing import Dict, List
from .syntax import Task, TaskAlias
from .task import TaskGroup
from .argparsing import CommandlineParsingHelper
from importlib.machinery import SourceFileLoader

CURRENT_SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))


class Context:
    _imported_tasks: Dict[str, Task]
    _task_aliases: Dict[str, TaskAlias]
    _compiled: Dict[str, Task]

    def __init__(self, tasks: List[Task], aliases: List[TaskAlias]):
        self._imported_tasks = {}
        self._task_aliases = {}

        for task in tasks:
            self._add_component(task)

        for alias in aliases:
            self._add_task(alias)

    @classmethod
    def merge(cls, first, second):
        """ Add one context to other context. Produces immutable new context. """

        new_ctx = cls([], [])

        for context in [first, second]:
            context: Context

            for name, component in context._imported_tasks.items():
                new_ctx._add_component(component)

            for name, task in context._task_aliases.items():
                new_ctx._add_task(task)

        return new_ctx

    def compile(self) -> None:
        """ Resolve all objects in the context. Should be called only, when all contexts were merged """

        self._compiled = self._imported_tasks

        for name, details in self._task_aliases.items():
            self._compiled[name] = self._resolve_alias(details)

    def find_task_by_name(self, name: str) -> Task:
        try:
            return self._compiled[name]
        except KeyError:
            raise Exception(('Task "%s" is not defined. Check if it is defined, or' +
                            ' imported, or if the spelling is correct.') % name)

    def _add_component(self, component: Task) -> None:
        self._imported_tasks[component.to_full_name()] = component

    def _add_task(self, task: TaskAlias) -> None:
        self._task_aliases[task.get_name()] = task

    def _resolve_alias(self, alias: TaskAlias) -> Task:
        """ Parse commandline args to fetch list of tasks to join into a group """

        args = CommandlineParsingHelper.create_grouped_arguments(alias.get_arguments())
        resolved_tasks = {}

        for argument_group in args:
            resolved_task = self.find_task_by_name(argument_group.name())
            resolved_task.set_env(alias.get_env())
            resolved_task.set_args(argument_group.args())

            resolved_tasks[argument_group.name()] = resolved_task

        return Task(TaskGroup(resolved_tasks))


class ContextFactory:
    """
    Takes responsibility of loading all tasks defined in USER PROJECT, USER HOME and GLOBALLY
    """

    @staticmethod
    def _load_context_from_directory(path: str) -> Context:
        if not os.path.isdir(path):
            raise Exception('Path "%s" font found' % path)

        makefile_path = path + '/makefile.py'

        if not os.path.isfile(makefile_path):
            raise Exception('makefile.py not found at path "%s"' % makefile_path)

        makefile = SourceFileLoader("Makefile", makefile_path).load_module()

        return Context(
            tasks=makefile.IMPORTS if "IMPORTS" in dir(makefile) else [],
            aliases=makefile.TASKS if "TASKS" in dir(makefile) else []
        )

    def create_unified_context(self, chdir: str = '') -> Context:
        """
        Creates a merged context in order:
        - Internal/Core (this package)
        - System-wide (/usr/lib/rkd)
        - User-home ~/.rkd
        - Application (current directory ./.rkd)
        :return:
        """

        paths = [
            CURRENT_SCRIPT_PATH + '/internal',
            '/usr/lib/rkd',
            os.path.expanduser('~/.rkd'),
            chdir + './.rkd'
        ]

        ctx = Context([], [])

        for path in paths:
            if os.path.isdir(path) and os.path.isfile(path + '/makefile.py'):
                ctx = Context.merge(ctx, self._load_context_from_directory(path))

        ctx.compile()
        return ctx
