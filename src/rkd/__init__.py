#!/usr/bin/env python3

import sys
import os
from .argparsing import CommandlineParsingHelper
from .context import ContextFactory, Context
from .resolver import TaskResolver
from .validator import TaskDeclarationValidator
from .executor import OneByOneTaskExecutor
from .exception import TaskNotFoundException


class RiotKitDoApplication:
    _ctx: Context
    _tasks_to_execute = []

    def main(self):
        if not sys.argv[1:]:
            self.print_banner_and_exit()

        try:
            # load context of components
            self._ctx = ContextFactory().create_unified_context()

            resolver = TaskResolver(self._ctx)
            executor = OneByOneTaskExecutor(self._ctx)

            # iterate over each task, parse commandline arguments
            requested_tasks = CommandlineParsingHelper.create_grouped_arguments([':init'] + sys.argv[1:])

            # validate all tasks
            resolver.resolve(requested_tasks, TaskDeclarationValidator.assert_declaration_is_valid)

            # execute all tasks
            resolver.resolve(requested_tasks, executor.execute)

        except TaskNotFoundException as e:
            print(e)
            sys.exit(1)

        executor.get_observer().execution_finished()

        sys.exit(1 if executor.get_observer().has_at_least_one_failed_task() else 0)

    @staticmethod
    def print_banner_and_exit():
        with open(os.path.dirname(os.path.realpath(__file__)) + '/misc/banner.txt', 'rb') as banner_file:
            print(banner_file.read().replace(b'\\x1B', b'\x1B').decode('utf-8'))

        sys.exit(0)

def main():
    app = RiotKitDoApplication()
    app.main()


if __name__ == '__main__':
    main()
