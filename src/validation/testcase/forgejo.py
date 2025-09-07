# SPDX-FileCopyrightText: 2023-present Contributors to the Packit Project.
#
# SPDX-License-Identifier: MIT

from functools import cached_property

from ogr.abstract import CommitFlag, CommitStatus
from ogr.services.forgejo import ForgejoProject

from validation.testcase.base import Testcase


def _get_hello_spec_content() -> str:
    """Return the hello.spec file content."""

    return """Name:           hello
Version:        2.12.2
Release:        %autorelease
Summary:        Prints a familiar, friendly greeting
# All code is GPLv3+.
# Parts of the documentation are under GFDL
License:        GPL-3.0-or-later AND GFDL-1.3-or-later
URL:            https://www.gnu.org/software/hello/
Source0:        https://ftp.gnu.org/gnu/hello/hello-%{version}.tar.gz
Source1:        https://ftp.gnu.org/gnu/hello/hello-%{version}.tar.gz.sig
Source2:        https://ftp.gnu.org/gnu/gnu-keyring.gpg

BuildRequires:  gcc
BuildRequires:  gnupg2
BuildRequires:  make
Recommends:     info
Provides:       bundled(gnulib)

%description
The GNU Hello program produces a familiar, friendly greeting.
Yes, this is another implementation of the classic program that
prints "Hello, world!" when you run it.

However, unlike the minimal version often seen, GNU Hello processes
its argument list to modify its behavior, supports greetings in many
languages, and so on. The primary purpose of GNU Hello is to
demonstrate how to write other programs that do these things; it
serves as a model for GNU coding standards and GNU maintainer
practices.


%prep
%{gpgverify} --keyring='%{SOURCE2}' --signature='%{SOURCE1}' --data='%{SOURCE0}'
%setup -q


%build
%configure
%make_build


%install
%make_install
rm -f %{buildroot}%{_infodir}/dir
%find_lang hello


%check
make check


%files -f hello.lang
%license COPYING
%{_mandir}/man1/hello.1*
%{_bindir}/hello
%{_infodir}/hello.info*


%changelog
%autochangelog
"""


class ForgejoTestcase(Testcase):
    project: ForgejoProject

    @property
    def account_name(self):
        return self.deployment.forgejo_account_name

    @cached_property
    def copr_project_name(self) -> str:
        return f"{self.project.service.hostname}-{self.project.namespace}-hello-world-{self.pr.id}"

    def get_status_name(self, status: CommitFlag) -> str:
        return status.context

    def create_file_in_new_branch(self, branch: str):
        import base64
        
        self.pr_branch_ref = self.project.api.repo_create_branch(
            owner=self.project.namespace,
            repo=self.project.repo,
            new_branch_name=branch,
            old_ref_name="main"
        )

        spec_content = _get_hello_spec_content()
        
        content = base64.b64encode(spec_content.encode()).decode()
        self.project.api.repo_create_file(
            owner=self.project.namespace,
            repo=self.project.repo,
            filepath="hello.spec",
            content=content,
            branch=branch,
            message="Opened PR trigger"
        )

    def get_statuses(self) -> list[CommitFlag]:
        all_statuses = list(self.project.get_commit_statuses(commit=self.head_commit))
        
        filtered_statuses = [
            status
            for status in all_statuses
            if any(keyword in status.context.lower() for keyword in [
                "packit", 
                "copr", 
                "build", 
                "test",
                self.deployment.app_name.lower(),
                self.deployment.forgejo_account_name.lower()
            ])
        ]
        return filtered_statuses

    def is_status_successful(self, status: CommitFlag) -> bool:
        return status.state == CommitStatus.success

    def is_status_completed(self, status: CommitFlag) -> bool:
        return status.state not in [
            CommitStatus.running,
            CommitStatus.pending,
        ]

    def delete_previous_branch(self, branch: str):
        try:
            self.project.api.repo_delete_branch(
                owner=self.project.namespace,
                repo=self.project.repo,
                branch=branch
            )
        except Exception:
            return

    def update_file_and_commit(self, path: str, commit_msg: str, content: str, branch: str):
        import base64
        
        current_content = self.project.get_file_content(path=path, ref=branch)
        current_sha = self.project.api.repo_get_raw_file(
            owner=self.project.namespace,
            repo=self.project.repo,
            filepath=path,
            ref=branch
        ).sha
        
        # Update the file
        encoded_content = base64.b64encode(content.encode()).decode()
        self.project.api.repo_update_file(
            owner=self.project.namespace,
            repo=self.project.repo,
            filepath=path,
            content=encoded_content,
            sha=current_sha,
            branch=branch,
            message=commit_msg
        )

    def create_empty_commit(self, branch: str, commit_msg: str) -> str:
        import base64
        import time
        
        # Create a temporary file with timestamp to ensure it's unique
        temp_filename = f"temp_commit_{int(time.time())}.txt"
        content = base64.b64encode(f"Push trigger commit: {commit_msg}".encode()).decode()
        
        # Create the file
        response = self.project.api.repo_create_file(
            owner=self.project.namespace,
            repo=self.project.repo,
            filepath=temp_filename,
            content=content,
            branch=branch,
            message=commit_msg
        )
        
        return response.commit.sha

    def create_pr(self):
        """
        Create a new PR for Forgejo, skipping the .packit.yaml fix since we're using a custom spec file.
        """
        source_branch = f"test/{self.deployment.name}/opened_pr"
        pr_title = f"Basic test case ({self.deployment.name}): opened PR trigger"
        self.delete_previous_branch(source_branch)
        # Delete the PR from the previous test run if it exists.
        existing_pr = [pr for pr in self.project.get_pr_list() if pr.title == pr_title]
        if len(existing_pr) == 1:
            existing_pr[0].close()

        self.create_file_in_new_branch(source_branch)
        
        self.pr = self.project.create_pr(
            title=pr_title,
            body="This test case is triggered automatically by our validation script.",
            target_branch=self.project.default_branch,
            source_branch=source_branch,
        )
        self.head_commit = self.pr.head_commit
