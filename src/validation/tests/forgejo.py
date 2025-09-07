# SPDX-FileCopyrightText: 2023-present Contributors to the Packit Project.
#
# SPDX-License-Identifier: MIT

from os import getenv

from ogr import ForgejoService
from ogr.services.forgejo import ForgejoProject

from validation.deployment import AVANT_INFO
from validation.testcase.forgejo import ForgejoTestcase
from validation.tests.base import Tests


class ForgejoTests(Tests):
    test_case_kls = ForgejoTestcase

    def __init__(
        self,
        instance_url="https://codeberg.org",
        namespace="avant",
        token_name="FORGEJO_TOKEN",
    ):
        forgejo_service = ForgejoService(token=getenv(token_name), instance_url=instance_url)
        self.project: ForgejoProject = forgejo_service.get_project(
            repo="hello-world",
            namespace=namespace,
        )

    async def run(self):
        """Override run method to use AVANT_INFO deployment instead of default DEPLOYMENT."""
        import asyncio
        import logging
        from validation.utils.trigger import Trigger

        loop = asyncio.get_event_loop()
        tasks = set()

        prs_for_comment = [
            pr for pr in self.project.get_pr_list() if pr.title.startswith("Test VM Image builds")
        ]
        if prs_for_comment:
            msg = (
                "Run testcases where the build is triggered by a "
                f"‹vm-image-build› comment for {self.project.service.instance_url}"
            )
        else:
            msg = (
                "No testcases found where the build is triggered by a "
                f"‹vm-image-build› comment for {self.project.service.instance_url}"
            )
        logging.warning(msg)
        for pr in prs_for_comment:
            task = loop.create_task(
                self.test_case_kls(
                    project=self.project,
                    pr=pr,
                    trigger=Trigger.comment,
                    deployment=AVANT_INFO,
                    comment=AVANT_INFO.pr_comment_vm_image_build,
                ).run_test(),
            )

            tasks.add(task)
            task.add_done_callback(tasks.discard)

        prs_for_comment = [
            pr for pr in self.project.get_pr_list() if pr.title.startswith("Basic test case:")
        ]
        if prs_for_comment:
            msg = (
                "Run testcases where the build is triggered by a "
                f"‹build› comment for {self.project.service.instance_url}"
            )
        else:
            msg = (
                "No testcases found where the build is triggered by a "
                f"‹build› comment for {self.project.service.instance_url}"
            )
        logging.warning(msg)
        for pr in prs_for_comment:
            task = loop.create_task(
                self.test_case_kls(
                    project=self.project,
                    pr=pr,
                    trigger=Trigger.comment,
                    deployment=AVANT_INFO,
                ).run_test(),
            )

            tasks.add(task)
            task.add_done_callback(tasks.discard)

        pr_for_push = [
            pr
            for pr in self.project.get_pr_list()
            if pr.title.startswith(AVANT_INFO.push_trigger_tests_prefix)
        ]
        if pr_for_push:
            msg = (
                "Run testcase where the build is triggered by push "
                f"for {self.project.service.instance_url}"
            )
        else:
            msg = (
                "No testcase found where the build is triggered by push "
                f"for {self.project.service.instance_url}"
            )
        logging.warning(msg)
        if pr_for_push:
            task = loop.create_task(
                self.test_case_kls(
                    project=self.project,
                    pr=pr_for_push[0],
                    trigger=Trigger.push,
                    deployment=AVANT_INFO,
                ).run_test(),
            )

            tasks.add(task)
            task.add_done_callback(tasks.discard)

        msg = (
            "Run testcase where the build is triggered by opening "
            f"a new PR {self.project.service.instance_url}"
        )
        logging.info(msg)

        task = loop.create_task(
            self.test_case_kls(project=self.project, deployment=AVANT_INFO).run_test(),
        )
        tasks.add(task)
        task.add_done_callback(tasks.discard)


