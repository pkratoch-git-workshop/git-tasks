#!/usr/bin/env python3

import argparse
import git
import sys


class TaskException(Exception):
    pass


class TaskCheckException(TaskException):
    def __init__(self, message):
        super().__init__("CHECK FAILED: %s" % message)


class Task():
    branch_names = []

    def __init__(self):
        self.repo = git.Repo('.')

    def reset_branches(self):
        """Delete all branches for this task and checkout them again from origin."""
        self.repo.git.checkout('main')
        for branch_name in self.branch_names:
            try:
                self.repo.delete_head(branch_name, force=True)
            except git.exc.GitCommandError:
                pass
            self.repo.git.checkout('origin/' + branch_name, b=branch_name)
        self.repo.git.checkout('main')

    def iter_commits(self, branch_name):
        """Iterate over commits that are in given branch (on top of the tasks branch)."""
        main_head_heaxsha = next(self.repo.iter_commits('origin/tasks')).hexsha
        for commit in self.repo.iter_commits(branch_name):
            if commit.hexsha == main_head_heaxsha:
                break
            yield commit

    def check_old_commits_unchanged(self, old_branch, new_branch):
        """Check all the commits in old branch are unchanged in the new branch (have the same hexsha)."""
        new_hexshas = [commit.hexsha for commit in self.iter_commits(new_branch)]
        new_summaries = [commit.summary for commit in self.iter_commits(new_branch)]

        for commit in self.iter_commits(old_branch):
            if commit.hexsha not in new_hexshas:
                if commit.summary not in new_summaries:
                    raise TaskCheckException('A commit is missing: %s' % commit.summary)
                else:
                    raise TaskCheckException('A commit was unexpectedly modified: %s' % commit.summary)

    def check_commits_count(self, branch, expected_commits_count):
        commits_count = len([commit for commit in self.iter_commits(branch)])
        diff = abs(commits_count - expected_commits_count)
        msg = 'Unexpected number of commits in branch {branch} ({diff} {quantifier} than expected).'
        if commits_count > expected_commits_count:
            raise TaskCheckException(msg.format(branch=branch, diff=diff, quantifier='more'))
        if commits_count < expected_commits_count:
            raise TaskCheckException(msg.format(branch=branch, diff=diff, quantifier='less'))


class Merge(Task):
    branch_names = ['merge-main', 'merge-feature']

    def start(self):
        self.reset_branches()

        print("""
===========
Task: merge
===========

Merge the `merge-feature` branch into the `merge-main` branch (and create a merge commit in the process).

If the history looks like this:

                  A---B---C feature
                 /
            D---E---F---G main

Then the result should look like this:

                  A---B---C feature
                 /         \\
            D---E---F---G---H main

The merge commit can contain a message describing the whole feature that was merged.

(To show only task-related branches in gitk: gitk --branches=merge-*)
""")


    def check(self):
        # Check all commits from the origin/merge-main and origin/merge-feature branches are present.
        self.check_old_commits_unchanged('origin/merge-main', 'merge-main')
        self.check_old_commits_unchanged('origin/merge-feature', 'merge-main')

        # Check the commits count (old ones, plus one merge commit)
        self.check_commits_count('merge-main', 7)

        # Check last commit is the new merge commit
        last_commit = next(self.iter_commits('merge-main'))

        old_hexshas = []
        old_summaries = []
        for commit in self.iter_commits('origin/merge-main'):
            old_hexshas.append(commit.hexsha)
            old_summaries.append(commit.summary)
        for commit in self.iter_commits('origin/merge-feature'):
            old_hexshas.append(commit.hexsha)
            old_summaries.append(commit.summary)

        if last_commit.hexsha in old_hexshas:
            raise TaskCheckException('The last commit is not new: %s' % last_commit.summary)
        if last_commit.summary in old_summaries:
            raise TaskCheckException('The last commit is probably not new: %s' % last_commit.summary)

        print("OK")


class Rebase(Task):
    branch_names = ['rebase-main', 'rebase-feature']

    def start(self):
        self.reset_branches()

        print("""
============
Task: rebase
============

Rebase the `rebase-feature` branch on top of the `rebase-main` branch.

If the history looks like this:

                  A---B---C feature
                 /
            D---E---F---G main

Then the result should look like this:

                          A'--B'--C' feature
                         /
            D---E---F---G main

(To show only task-related branches in gitk: gitk --branches=rebase-*)
""")


    def check(self):
        # Check all commits from the origin/rebase-main are present in both rebase-main and rebase-feature.
        self.check_old_commits_unchanged('origin/rebase-main', 'rebase-main')
        self.check_old_commits_unchanged('origin/rebase-main', 'rebase-feature')

        # Check the commits count
        self.check_commits_count('rebase-main', 4)
        self.check_commits_count('rebase-feature', 6)

        # Check the commit order
        expected_summaries = [
            'Add explanations to the branching commands',
            'Add basic cheatsheet for working with branches',
            'Add commands for working with remote rpositories',
            'Add explanations to individual commands',
            'Add commands for inspecting the repo',
            'Add cheatseet with basic git commands',
        ]

        main_summaries = [commit.summary for commit in self.iter_commits('rebase-main')]
        if main_summaries != expected_summaries[2:]:
            raise TaskCheckException('The commits in rebase-main branch changed.')

        feature_summaries = [commit.summary for commit in self.iter_commits('rebase-feature')]
        if feature_summaries != expected_summaries:
            raise TaskCheckException(
                'Unexpected commits in rebase-feature branch. '
                'Expected summaries:\n%s' % '\n'.join(expected_summaries)
            )

        print("OK")


def main():
    # Define tasks:
    task_classes = {
        'merge': Merge,
        'rebase': Rebase,
    }

    parser = argparse.ArgumentParser()
    parser.add_argument('taskname', help='Name of a task')
    parser.add_argument('command', choices=['start', 'check'], help='Command to run')
    args = parser.parse_args()

    if args.taskname not in task_classes:
        TaskException('Task "%s" not found.')

    task = task_classes[args.taskname]()
    func = getattr(task, args.command, None)
    if not callable(func):
        raise TaskException('Command "%s" for task "%s" not found.' % (args.command, args.taskname))
    func()


if __name__ == "__main__":
    try:
        main()
    except TaskException as e:
        print(e)
        sys.exit(1)
