#!/usr/bin/env python3

import argparse
import subprocess
import sys


FORMAT_HASH = '%H'
FORMAT_SUMMARY = '%s'


class TaskException(Exception):
    pass


class TaskCheckException(TaskException):
    def __init__(self, message):
        super().__init__("CHECK FAILED: %s" % message)


def branch_list():
    """Get list of branches."""
    result = subprocess.run(['git', 'branch'], stdout=subprocess.PIPE, check=True)
    return [branch.strip() for branch in result.stdout.decode("utf-8").strip().split('\n')]


def current_branch():
    """Get name of the current branch."""
    result = subprocess.run(['git', 'branch', '--show-current'], stdout=subprocess.PIPE, check=True)
    return result.stdout.decode("utf-8").strip()


def switch_branch(branch):
    """Switch current branch."""
    subprocess.run(['git', 'checkout', branch], check=True)


def commit_log(branch_name, pretty_format=FORMAT_HASH):
    """Get commit log of commits in given branch (on top of the tasks branch)."""
    result = subprocess.run(
        ['git', 'log', '--pretty=' + pretty_format, 'origin/tasks..' + branch_name],
        stdout=subprocess.PIPE,
        check=True
    )
    return result.stdout.decode("utf-8").strip().split('\n')


def commit_show(commit, pretty_format=FORMAT_HASH):
    """Get commit information in particular format."""
    result = subprocess.run(
        ['git', 'show', '--pretty=' + pretty_format, '-s', commit], stdout=subprocess.PIPE, check=True
    )
    return result.stdout.decode("utf-8").strip()


def check_branches_identical(old_branch, new_branch):
    """Check all the commits in the two branches are the same."""
    if commit_log(old_branch) != commit_log(new_branch):
        raise TaskCheckException('The `%s` branch changed.' % new_branch)


def check_old_commits_unchanged(old_branch, new_branch):
    """Check all the commits in old branch are unchanged in the new branch
    (have the same hexsha)."""
    new_hexshas = commit_log(new_branch)
    new_summaries = commit_log(new_branch, FORMAT_SUMMARY)

    for hexsha in commit_log(old_branch):
        if hexsha not in new_hexshas:
            summary = commit_show(hexsha, FORMAT_SUMMARY)
            if summary not in new_summaries:
                raise TaskCheckException('A commit is missing: %s' % summary)
            else:
                raise TaskCheckException('A commit was unexpectedly modified: %s' % summary)


def check_commits_count(branch, expected_commits_count):
    commits_count = len(commit_log(branch))
    diff = abs(commits_count - expected_commits_count)
    msg = (
        'Unexpected number of commits in branch {branch} ({diff} {quantifier} than expected).'
    )
    if commits_count > expected_commits_count:
        raise TaskCheckException(msg.format(branch=branch, diff=diff, quantifier='more'))
    if commits_count < expected_commits_count:
        raise TaskCheckException(msg.format(branch=branch, diff=diff, quantifier='less'))


def check_summaries(branch, expected, skip=0):
    actual = commit_log(branch, FORMAT_SUMMARY)
    if actual[skip:] != expected[skip:]:
        raise TaskCheckException(
            'Unexpected commits in the `%s` branch. Expected summaries: \n%s' % (branch, '\n'.join(expected))
        )


def git_diff(*args):
    result = subprocess.run(['git', 'diff', *args], stdout=subprocess.PIPE, check=True)
    return result.stdout.decode("utf-8").strip()


class Task():
    branch_names = []

    def reset_branches(self):
        """Delete all branches for this task and checkout them again from origin."""
        subprocess.run(['git', 'reset', '--hard'])
        switch_branch('main')
        for branch_name in self.branch_names:
            subprocess.run(['git', 'branch', '-D', branch_name])
            subprocess.run(
                ['git', 'checkout', '-b', branch_name, 'origin/' + branch_name], check=True
            )
        switch_branch('main')


class CherryPick(Task):
    branch_names = ['cherry-pick-main', 'cherry-pick-feature']

    def start(self):
        self.reset_branches()

        print("""
=================
Task: cherry-pick
=================

Cherry-pick into the `cherry-pick-main` branch all the commits that modified \
`source/cheatsheet.md` file in the `cherry-pick-feature` branch that are not yet in the \
`cherry-pick-main` branch.

If the history looks like this:

                      A---B---C---D---E---F feature
                     /
            G---H---I---J main

Then the result should look like this:

                      A---B---C---D---E---F feature
                     /
            G---H---I---J---C`--D` main

(To show only task-related branches in gitk: gitk --branches=cherry-pick-*)
""")


    def check(self):
        # Check the cherry-pick-feature branch hasn't changed.
        check_branches_identical('origin/cherry-pick-feature', 'cherry-pick-feature')

        # Check all commits from the origin/cherry-pick-main are present in the cherry-pick-main.
        check_old_commits_unchanged('origin/cherry-pick-main', 'cherry-pick-main')

        # Check the commits count
        check_commits_count('cherry-pick-main', 6)

        # Check the commit order
        expected_summaries = [
            'Escape the diagram in cheatsheet',
            'Add picture of the basic git workflow',
            'Add commands for working with remote rpositories',
            'Add explanations to individual commands',
            'Add commands for inspecting the repo',
            'Add cheatsheet with basic git commands',
        ]
        check_summaries('cherry-pick-main', expected_summaries)

        print("OK")


class ConflictCherryPick(Task):
    branch_names = ['conflict-cherry-pick-main', 'conflict-cherry-pick-feature']

    def start(self):
        self.reset_branches()

        print("""
==========================
Task: conflict-cherry-pick
==========================

Cherry-pick into the `conflict-cherry-pick-main` branch all the commits that modified \
`source/cheatsheet.md` file in the `conflict-cherry-pick-feature` branch that are not yet in the \
`conflict-cherry-pick-main` branch.

If the history looks like this:

                  A---B---C---D---E---F feature
                 /
            G---H---I---J main

Then the result should look like this:

                  A---B---C---D---E---F feature
                 /
            G---H---I---J---C`--D` main

(To show only task-related branches in gitk: gitk --branches=conflict-cherry-pick-*)
""")


    def check(self):
        # Check the conflict-cherry-pick-feature branch hasn't changed.
        check_branches_identical('origin/conflict-cherry-pick-feature', 'conflict-cherry-pick-feature')

        # Check all commits from the origin/conflict-cherry-pick-main are present in the conflict-cherry-pick-main.
        check_old_commits_unchanged('origin/conflict-cherry-pick-main', 'conflict-cherry-pick-main')

        # Check the commits count
        check_commits_count('conflict-cherry-pick-main', 6)

        # Check the commit order
        expected_summaries = [
            'Escape the diagram in cheatsheet',
            'Add picture of the basic git workflow',
            'Add commands for working with remote rpositories',
            'Add explanations to individual commands',
            'Add commands for inspecting the repo',
            'Add cheatsheet with basic git commands',
        ]
        check_summaries('conflict-cherry-pick-main', expected_summaries)

        print("OK")


class Merge(Task):
    branch_names = ['merge-main', 'merge-feature']

    def start(self):
        self.reset_branches()

        print("""
===========
Task: merge
===========

Merge the `merge-feature` branch into the `merge-main` branch (and create a merge commit in the \
process).

If the history looks like this:

                      A---B feature
                     /
            C---D---E---F main

Then the result should look like this:

                      A---B feature
                     /     \\
            C---D---E---F---G main

The merge commit can contain a message describing the whole feature that was merged.

(To show only task-related branches in gitk: gitk --branches=merge-*)
""")


    def check(self):
        # Check the merge-feature branch hasn't changed.
        check_branches_identical('origin/merge-feature', 'merge-feature')

        # Check all commits from the origin/merge-main and origin/merge-feature branches are
        # present in merge-main.
        check_old_commits_unchanged('origin/merge-main', 'merge-main')
        check_old_commits_unchanged('origin/merge-feature', 'merge-main')

        # Check the commits count (old ones, plus one merge commit)
        check_commits_count('merge-main', 7)

        # Check last commit is the new merge commit
        last_commit_hexsha = commit_show('merge-main')
        last_commit_summary = commit_show('merge-main', FORMAT_SUMMARY)

        old_hexshas = commit_log('origin/merge-main') + commit_log('origin/merge-feature')
        old_summaries = commit_log('origin/merge-main', FORMAT_SUMMARY)
        old_summaries += commit_log('origin/merge-feature', FORMAT_SUMMARY)

        if last_commit_hexsha in old_hexshas:
            raise TaskCheckException('The last commit is not new: %s' % last_commit_summary)
        if last_commit_summary in old_summaries:
            raise TaskCheckException(
                'The last commit is probably not new: %s' % last_commit_summary
            )

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

                  A---B feature
                 /
            D---E---F---G main

Then the result should look like this:

                          A'--B' feature
                         /
            D---E---F---G main

(To show only task-related branches in gitk: gitk --branches=rebase-*)
""")


    def check(self):
        # Check the rebase-main branch hasn't changed.
        check_branches_identical('origin/rebase-main', 'rebase-main')

        # Check all commits from the origin/rebase-main are present in the rebase-feature.
        check_old_commits_unchanged('origin/rebase-main', 'rebase-feature')

        # Check the commits count
        check_commits_count('rebase-feature', 6)

        # Check the commit order
        expected_summaries = [
            'Add explanations to the branching commands',
            'Add basic cheatsheet for working with branches',
            'Add commands for working with remote rpositories',
            'Add explanations to individual commands',
            'Add commands for inspecting the repo',
            'Add cheatsheet with basic git commands',
        ]
        check_summaries('rebase-feature', expected_summaries)

        print("OK")


class ConflictRebase(Task):
    branch_names = ['conflict-rebase-main', 'conflict-rebase-feature']

    def start(self):
        self.reset_branches()

        print("""
=====================
Task: conflict-rebase
=====================

Rebase the `conflict-rebase-feature` branch on top of the `conflict-rebase-main` branch. 

In this scenario, you will encounter a conflict and will need to resolve it.

If the history looks like this:

                  A---B feature
                 /
            D---E---F---G main

Then the result should look like this:

                          A'--B' feature
                         /
            D---E---F---G main

(To show only task-related branches in gitk: gitk --branches=conflict-rebase-*)
""")


    def check(self):
        # Check the conflict-rebase-main branch hasn't changed.
        check_branches_identical('origin/conflict-rebase-main', 'conflict-rebase-main')

        # Check all commits from the origin/conflict-rebase-main are present in the conflict-rebase-feature.
        check_old_commits_unchanged('origin/conflict-rebase-main', 'conflict-rebase-feature')

        # Check the commits count
        check_commits_count('conflict-rebase-feature', 5)

        # Check the commit order
        expected_summaries = [
            'Add commands for working with branches',
            'Add commands for working with remote rpositories',
            'Add explanations to individual commands',
            'Add commands for inspecting the repo',
            'Add cheatsheet with basic git commands',
        ]
        check_summaries('conflict-rebase-feature', expected_summaries)

        # Check the source/cheatsheet.md file is correct
        expected_start = [
            "Git Cheatsheet",
            "==============",
            "git add     - add file contents to the index",
            "git commit  - record changes to the repository",
        ]
        expected_lines = [
            "git status  - show the working tree status",
            "git log     - show commit logs",
            "git show    - show various types of objects",
            "git branch - list, create, or delete branches",
            "git switch - switch branches",
            "git push    - update remote refs along with associated objects",
            "git fetch   - download objects and refs from another repository",
        ]
        if current_branch() != 'conflict-rebase-feature':
            switch_branch('conflict-rebase-feature')
        with open('source/cheatsheet.md') as f:
            lines = [line.strip() for line in f if line.strip()]
        if lines[:4] != expected_start:
            raise TaskCheckException(
                'The content of source/cheatsheet.md is different than expected. '
                'It should start with (without empty lines):\n%s' % '\n'.join(expected_start)
            )
        if sorted(lines[4:]) != sorted(expected_lines):
            raise TaskCheckException(
                'The content of source/cheatsheet.md is different than expected. Expected '
                'lines (without empty lines):\n%s' % '\n'.join(expected_start + expected_lines)
            )

        # Check the last commit adds only commands for working with branches 
        expected_added_commands = [
            "+git branch - list, create, or delete branches",
            "+git switch - switch branches",
        ]
        diff_last_commit = git_diff('conflict-rebase-feature^', 'conflict-rebase-feature').split('\n')
        added_commands = [line for line in diff_last_commit if line.startswith("+git")]
        removed_commands = [line for line in diff_last_commit if line.startswith("-git")]
        if removed_commands or sorted(added_commands) != expected_added_commands:
            raise TaskCheckException(
                'The last commit should only add commands for working with branches. '
                'Expected added commands:\n%s' % '\n'.join(expected_added_commands)
            )

        print("OK")


class ResetHard(Task):
    branch_names = ['reset-hard-main']

    def start(self):
        self.reset_branches()

        print("""
================
Task: reset-hard
================

Reset the `reset-hard-main` branch to the point right before the last commit. Reset both the \
index and the working tree, i.e. completely discard all changes introduced by the commit.

If the history looks like this:

            A---B---C---D---E---F main

Then the result of resetting to commit B should look like this:

            A---B---C---D---E main

(To show only task-related branches in gitk: gitk --branches=reset-hard-*)
""")

    def check(self):
        # Check all commits from the origin/reset-hard-main are present in reset-hard-main.
        new_hexshas = commit_log('reset-hard-main')
        new_summaries = commit_log('reset-hard-main', FORMAT_SUMMARY)
        skip_first = True
        for hexsha in commit_log('origin/reset-hard-main'):
            if skip_first:
                skip_first = False
                continue
            if hexsha not in new_hexshas:
                summary = commit_show(hexsha, FORMAT_SUMMARY)
                if summary not in new_summaries:
                    raise TaskCheckException('A commit is missing: %s' % summary)
                else:
                    raise TaskCheckException(
                        'A commit was unexpectedly modified: %s' % summary
                    )

        # Check the commits count
        check_commits_count('reset-hard-main', 5)

        # Check the commit order
        expected_summaries = [
            'Add explanations to the branching commands',
            'Add basic cheatsheet for working with branches',
            'Add explanations to individual commands',
            'Add commands for inspecting the repo',
            'Add cheatsheet with basic git commands',
        ]
        check_summaries('reset-hard-main', expected_summaries)

        print("OK")

class ResetSoft(Task):
    branch_names = ['reset-soft-main']

    def start(self):
        self.reset_branches()

        print("""
================
Task: reset-soft
================

Reset the `reset-soft-main` branch to the point right before the last commit, but keep the index \
and the working tree.

(To show only task-related branches in gitk: gitk --branches=reset-soft-*)
""")


    def check(self):
        # Check all commits from the origin/reset-soft-main are present in reset-soft-main.
        new_hexshas = commit_log('reset-soft-main')
        new_summaries = commit_log('reset-soft-main', FORMAT_SUMMARY)
        skip_first = True
        for hexsha in commit_log('origin/reset-soft-main'):
            if skip_first:
                skip_first = False
                continue
            if hexsha not in new_hexshas:
                summary = commit_show(hexsha, FORMAT_SUMMARY)
                if summary not in new_summaries:
                    raise TaskCheckException('A commit is missing: %s' % summary)
                else:
                    raise TaskCheckException(
                        'A commit was unexpectedly modified: %s' % summary
                    )

        # Check the commits count
        check_commits_count('reset-soft-main', 5)

        # Check the commit order
        expected_summaries = [
            'Add explanations to the branching commands',
            'Add basic cheatsheet for working with branches',
            'Add explanations to individual commands',
            'Add commands for inspecting the repo',
            'Add cheatsheet with basic git commands',
        ]
        check_summaries('reset-soft-main', expected_summaries)

        diff_staged = git_diff('--staged')
        diff_resetted_commit = git_diff('origin/reset-soft-main^', 'origin/reset-soft-main')
        if diff_staged != diff_resetted_commit:
            raise TaskCheckException('The index is not the same as the resetted commit.')

        print("OK")


class Revert(Task):
    branch_names = ['revert-main']

    def start(self):
        self.reset_branches()

        print("""
============
Task: revert
============

In a branch `revert-main`, there is a commit with summary "Make the cheatsheet into a nice table" \
that breaks the markdown in the cheatsheet.md file. Revert this commit.

Note that you don't want to change the history of the `revert-main` branch, but to create new \
commit that is opposite to the one you want to undo.

If the history looks like this:

            A---B---C---D---E---F main

Then the result should look like this:

            A---B---C---D---E---F---D' main

(To show only task-related branches in gitk: gitk --branches=revert-*)
""")


    def check(self):
        # Check all commits from the origin/revert-main are present in revert-main.
        check_old_commits_unchanged('origin/revert-main', 'revert-main')

        # Check the commits count
        check_commits_count('revert-main', 7)

        # Check the commit order
        expected_summaries = [
            '<REVERT COMMIT>',
            'Add explanations to the branching commands',
            'Add basic cheatsheet for working with branches',
            'Make the cheatsheet into a nice table',
            'Add explanations to individual commands',
            'Add commands for inspecting the repo',
            'Add cheatsheet with basic git commands',
        ]
        check_summaries('revert-main', expected_summaries, skip=1)

        # Check the last commit is the correct reverted commit by comparing diffs
        commits = commit_log('revert-main')
        expected_diff = git_diff(commits[4], commits[3])
        revert_commit_diff = git_diff(commits[0], commits[1])
        if revert_commit_diff != expected_diff:
            raise TaskCheckException(
                'The last commit is not the reverted commit.\n\n'
                'Expected diff:\n\n%s\n\nActual diff:\n\n%s' % (expected_diff, revert_commit_diff))

        print("OK")


class ChangeMessage(Task):
    branch_names = ["change-message-tasks"]

    def start(self):
        self.reset_branches()

        print("""
====================
Task: change-message
====================

In a branch `change-message-tasks`, there are several commits that make up a complete poem by \
Emily Dickinson. The very first commit of the branch has a wrong commit message saying \
`Add title and author`. 

Use interactive rebase to replace the commit message, so that the new message is `Add 'After Great Pain' by Emily Dickinson.`

Make sure that the commit history remains unchanged, except for this one commit message.

""")

    def check(self):
        # Check the commits count
        check_commits_count('change-message-tasks', 2)

        # Check the commit order
        expected_summaries = [
            'Add text.',
            "Add 'After Great Pain' by Emily Dickinson.",
        ]

        main_summaries = commit_log('change-message-tasks', FORMAT_SUMMARY)
        if len(main_summaries) != len(expected_summaries):
            raise TaskCheckException(
                'The number of new commits in change-message-main branch differs from the '
                'expected number. Expected commit number: %s' % (len(expected_summaries))
            )

        # Check that the commit message has been changed.
        if main_summaries[1] != expected_summaries[1]:
            raise TaskCheckException(
                'The commit message seems not be changed correctly.\nCurrent message: '
                '%s\nExpected message: %s' % (main_summaries[1], expected_summaries[1]))

        print("OK")


class SquashCommit(Task):
    branch_names = ["squash-commits-tasks"]

    def start(self):
        self.reset_branches()

        print("""
====================
Task: squash-commits
====================

In a branch `squash-commits-tasks`, there are several commits that make up a complete poem by \
Emily Dickinson. Before we merge the content of this branch into `main`, we would like to squash \
the commits so that the whole added content is only represented by \
the very first commit. All following commits should be squashed into the first one. 

Use interactive rebase to squash the commits, so that there is only the very first commit left in \
the branch, while the content of the branch remains unchanged.

""")

    def check(self):

        # Check the commits count
        check_commits_count('squash-commits-tasks', 1)

        # Check the commit order.
        expected_summaries = [
            "Add 'Fame is a bee' by Emily Dickinson.",
        ]

        main_summaries = commit_log('squash-commits-tasks', FORMAT_SUMMARY)
        if len(main_summaries) != len(expected_summaries):
            raise TaskCheckException(
                'The number of new commits in squash-commits-tasks branch differs from the '
                'expected number. Expected commit number: %s' % (len(expected_summaries))
            )

        if main_summaries[0] != "Add 'Fame is a bee' by Emily Dickinson.":
            raise TaskCheckException(
                'The message of the first commit has changed, but it should be the same.\n'
                'Expected commit message: %s\nCurrent commit message: %s' % (
                    expected_summaries[0], main_summaries[0]
                )
             )

        # Check that there is no difference in content between the original and the squashed
        # repository.
        original = commit_show('origin/squash-commits-tasks')
        new = commit_show('squash-commits-tasks')
        diff = git_diff(original, new)
        if diff:
            raise TaskCheckException(
                'The content of the squashed branch is different from the original branch.\n'
                'See the diff: \n%s' % diff)

        print("OK")


class ReorganizeCommits(Task):
    branch_names = ["reorganize-commits-tasks"]

    def start(self):
        self.reset_branches()

        print("""
========================
Task: reorganize-commits
========================

In a branch `reorganize-commits-tasks`, there are several commits that make up two complete poems \
by Emily Dickinson. Before we merge the content of this branch into `main`, we would like to \
squash the commits so that the whole added content is only represented by two commits, each one \
for a particular poem.  

Use interactive rebase to reorganize, squash and reword the commits, so that there are only two \
commits left in the branch, while the content of the branch remains unchanged.

The final commits should be named `Poem 1: Add a poem.` and `Poem 2: Add a poem.`

""")

    def check(self):

        # Check the commits count
        check_commits_count('reorganize-commits-tasks', 2)

        # Check the commit order.
        expected_summaries = [
            "Poem 2: Add a poem.",
            "Poem 1: Add a poem.",
        ]

        main_summaries = commit_log('reorganize-commits-tasks', FORMAT_SUMMARY)
        if len(main_summaries) != len(expected_summaries):
            raise TaskCheckException(
                'The number of new commits in this branch differs from the expected number.'
                'Expected commit number: %s' % (len(expected_summaries))
            )

        if main_summaries[0] != "Poem 2: Add a poem.":
            raise TaskCheckException(
                'The message of the second commit differs from what is expected.\n'
                'Expected commit message: %s\nCurrent commit message: %s' % (
                    expected_summaries[0], main_summaries[0]
                )
             )

        if main_summaries[1] != "Poem 1: Add a poem.":
            raise TaskCheckException(
                'The message of the first commit differs from what is expected.\n'
                'Expected commit message: %s\nCurrent commit message: %s' % (
                    expected_summaries[1], main_summaries[1]
                )
             )

        # Check that there is no difference in content between the original and the squashed
        # repository.
        original = commit_show('origin/reorganize-commits-tasks')
        new = commit_show('reorganize-commits-tasks')
        diff = git_diff(original, new)
        if diff:
            raise TaskCheckException(
                'The content of the squashed branch is different from the original branch.\n'
                'See the diff: \n%s' % diff)

        print("OK")


class CommitAmend(Task):
    branch_names = ["commit-amend-tasks"]

    def start(self):
        self.reset_branches()

        print("""
==================
Task: commit-amend
==================

In the branch `commit-amend-tasks`, there is one commit that makes up a complete poem by Emily \
Dickinson. Unfortunately, one of the writers made a typo and left this mistake in the name of \
the author which is `Elimy` but should be `Emily`. Before we merge the content of this branch \
into `main`, we would like to correct the mistake before we do so.   

Since this is only a minor change and we have already squashed all the commits in the branch, do \
not produce an extra commit, but add the change to the existing commit instead. 

After the change, there should be one commit only in the branch with the same commit message as \
before!

""")

    def check(self):
        # Check the commits count
        check_commits_count('commit-amend-tasks', 1)

        # Check the commit order.
        expected_summaries = [
            "Add poem: Forever is composed of nows",
        ]

        main_summaries = commit_log('commit-amend-tasks', FORMAT_SUMMARY)
        if len(main_summaries) != len(expected_summaries):
            raise TaskCheckException(
                'The number of new commits in this branch differs from the expected number.'
                'Expected commit number: %s' % (len(expected_summaries))
            )

        if main_summaries[0] != "Add poem: Forever is composed of nows":
            raise TaskCheckException(
                'The message of the commit differs from what is expected.\n'
                'Expected commit message: %s\nCurrent commit message: %s' % (
                    expected_summaries[0], main_summaries[0]
                )
             )

        # Check that there is a difference in content between the original and the new commit.
        original = commit_show('origin/commit-amend-tasks')
        new = commit_show('commit-amend-tasks')
        diff = git_diff(original, new)
        if not diff:
            raise TaskCheckException(
                'The content of the branch seems not to be corrected! '
                'The text is the same as it was before.\n')
        else:
            if "+*By Emily Dickinson*" not in diff:
                raise TaskCheckException(
                    'The mistake was not corrected as expected.\n\n'
                    'See the diff:\n%s' % diff)

        print("OK")


class Stash(Task):
    branch_names = ["stash-tasks"]

    def start(self):
        self.reset_branches()

        print("""
===========
Task: stash
===========

In the branch `stash-tasks`, there is one commit that makes up a skeleton for your own poem. You \
should change the skeleton file into a text of your liking. Change some lines and save the file.

Unfortunately, before you could commit and push the changes, you have learnt that the remote \
branch has been rebased and you need to reset your local branch to the remote branch, but you do \
not want to lose any changes you have already made in your local branch.

Use stash to protect your changes and reset local branch onto the remote one.

""")

    def check(self):
        # Check the apply-stash-tasks branch hasn't changed.
        check_branches_identical('origin/stash-tasks', 'stash-tasks')

        # Check that there is a difference in content between the original and the new commit.
        original = commit_show('origin/stash-tasks')
        new = commit_show('stash-tasks')
        diff = git_diff(original, new)
        if diff:
            raise TaskCheckException(
                'The content of the branch is different from the original branch.\n'
                'See the diff: \n%s' % diff)

        # Check that there is a stash saved.
        result = subprocess.run(['git', 'stash', 'list'], stdout=subprocess.PIPE, check=True)
        stash_list = result.stdout.decode("utf-8").strip()
        if not stash_list:
            raise TaskCheckException(
                'Nothing has been put into stash. The content is not protected.\n\n'
                'Expected was something like "stash@{0}: WIP on stash-tasks: ..."')

        print("OK")


class ApplyStash(Task):
    branch_names = ["apply-stash-tasks"]

    def start(self):
        self.reset_branches()

        print("""
=================
Task: apply-stash
=================

In the branch `apply-stash-tasks`, there is one commit that makes up a skeleton for your own \
poem. You should change the skeleton file into a text of your liking. Change some lines and save \
    the file.

Unfortunately, before you could commit and push the changes, you have learnt that the remote \
branch has been rebased and you need to reset your local branch to the remote branch, but you do \
not want to lose any changes you have already made in your local branch.

Use stash to protect your changes and reset local branch onto the remote one. Then apply the \
stashed content and delete it from the stash. Stage the new content and commit it. Make the \
commit message be 'Add my favourite poem.'

""")

    def check(self):

        # Check the commits count
        check_commits_count('apply-stash-tasks', 2)

        # Check the commit order.
        expected_summaries = [
            "Add my favourite poem.",
            "Add a poem skeleton.",
        ]

        main_summaries = commit_log('apply-stash-tasks', FORMAT_SUMMARY)
        if len(main_summaries) != len(expected_summaries):
            raise TaskCheckException(
                'The number of commits in this branch differs from the expected number.'
                'Expected commit number: %s' % (len(expected_summaries))
            )

        if main_summaries[0] != "Add my favourite poem.":
            raise TaskCheckException(
                'The message of the commit differs from what is expected.\n'
                'Expected commit message: %s\nCurrent commit message: %s' % (
                    expected_summaries[0], main_summaries[0]
                )
             )

        # Check that there is a difference in content between the original and the new commit.
        original = commit_show('origin/apply-stash-tasks')
        new = commit_show('apply-stash-tasks')
        diff = git_diff(original, new)
        if not diff:
            raise TaskCheckException(
                'The content of the branch seems not to be correctly applied from stash!')

        # Check that there is a stash saved.
        result = subprocess.run(['git', 'stash', 'list'], stdout=subprocess.PIPE, check=True)
        stash_list = result.stdout.decode("utf-8").strip()

        if stash_list:
            raise TaskCheckException(
                'There is something in the stash, but the stash should be empty.\n\n'
                'See stash:\n%s' % stash_list)

        print("OK")


class ConflictRevert(Task):
    branch_names = ['conflict-revert-main']

    def start(self):
        self.reset_branches()

        print("""
=====================
Task: conflict-revert
=====================

In a branch `conflict-revert-main`, there is a commit with summary "Make the cheatsheet into a \
nice table" that breaks the markdown in the cheatsheet.md file. Revert this commit.

Note that you don't want to change the history of the `conflict-revert-main` branch, but to \
create new commit that is opposite to the one you want to undo.

In this scenario, you will encounter a conflict and will need to resolve it.

If the history looks like this:

            A---B---C---D---E---F---G main

Then the result should look like this:

            A---B---C---D---E---F---G---D' main

(To show only task-related branches in gitk: gitk --branches=conflict-revert-*)
""")


    def check(self):
        # Check all commits from the origin/conflict-revert-main are present in
        # conflict-revert-main.
        check_old_commits_unchanged('origin/conflict-revert-main', 'conflict-revert-main')

        # Check the commits count
        check_commits_count('conflict-revert-main', 8)

        # Check the commit order
        expected_summaries = [
            '<REVERT COMMIT>',
            'Add picture of the basic git workflow',
            'Add explanations to the branching commands',
            'Add basic cheatsheet for working with branches',
            'Make the cheatsheet into a nice table',
            'Add explanations to individual commands',
            'Add commands for inspecting the repo',
            'Add cheatsheet with basic git commands',
        ]
        check_summaries('conflict-revert-main', expected_summaries, skip=1)

        # Check the last commit is the correct reverted commit
        expected_lines = [
            'Git Cheatsheet',
            '==============',
            '- git add     - add file contents to the index',
            '- git commit  - record changes to the repository',
            '```',
            '+-----------+          +---------+             +------------+',
            '|  working  | -------> | staging | ----------> | repository |',
            '| directory | git add  |  area   | git commit  |            |',
            '+-----------+          +---------+             +------------+',
            '```',
            '- git status  - show the working tree status',
            '- git log     - show commit logs',
            '- git show    - show various types of objects',
        ]
        subprocess.run(['git', 'switch', 'conflict-revert-main'], check=True)
        with open('source/cheatsheet.md') as f:
            lines = [line.strip() for line in f if line.strip()]
        if lines != expected_lines:
            raise TaskCheckException(
                'The content of source/cheatsheet.md is different than expected. '
                'Expected lines (without empty lines):\n%s' % '\n'.join(expected_lines)
            )

        print("OK")


class NewBranch(Task):
    branch_names = ['new-branch-main']

    def start(self):
        self.reset_branches()

        print("""
================
Task: new-branch
================

Create a new branch named `new-branch` starting of the `new-branch-main` branch.
""")


    def check(self):
        # Check the new-branch-main branch hasn't changed.
        check_branches_identical('origin/new-branch-main', 'new-branch-main')

        # Check branch exists.
        if 'new-branch' not in branch_list() and '* new-branch' not in branch_list():
            raise TaskCheckException('Branch "new-branch" does not exist.')

        # Check new-branch is the same as new-branch-main.
        try:
            check_branches_identical('new-branch-main', 'new-branch')
        except TaskCheckException:
            raise TaskCheckException('The new branch is not on the top of the `new-branch-main` branch.')

        print("OK")


class Drop(Task):
    branch_names = ['drop-main']

    def start(self):
        self.reset_branches()

        print("""
==========
Task: drop
==========

In a branch `drop-main`, there is a commit with summary "Make the cheatsheet into a nice table" \
that breaks the markdown in the cheatsheet.md file.

Using an interactive rebase, drop this commit.

If the history looks like this:

            A---B---C---D---E---F main

Then the result should look like this:

            A---B---C---E---F main

(To show only task-related branches in gitk: gitk --branches=drop-*)
""")


    def check(self):
        # Check the commits count
        check_commits_count('drop-main', 5)

        # Check the commit order
        expected_summaries = [
            'Add explanations to the branching commands',
            'Add basic cheatsheet for working with branches',
            'Add explanations to individual commands',
            'Add commands for inspecting the repo',
            'Add cheatsheet with basic git commands',
        ]
        check_summaries('drop-main', expected_summaries)

        print("OK")


class Blame(Task):
    branch_names = ['blame-main']

    def start(self):
        self.reset_branches()

        print("""
===========
Task: blame
===========

In a branch `blame-main`, who last changed the line 78 in the file `source/cheatsheet.md`?

Who originally introduced the typo in the word "download"?

(To show only task-related branches in gitk: gitk --branches=blame-*)
""")

    def check(self):
        answer = input(
            "In a branch `blame-main`, who last changed the line 78 in the file "
            "`source/cheatsheet.md`? "
        )
        if answer.strip() != "Dave":
            raise TaskCheckException('This is not the correct answer.')
        answer = input('Who originally introduced the typo in the word "download"? ')
        if answer.strip() != "Chloe":
            raise TaskCheckException('This is not the correct answer.')
        print("OK")


class Add(Task):
    branch_names = ['simple']

    def start(self):
        self.reset_branches()

        print("""
=========
Task: add
=========

Create two new files named "day" and "night" and add the "day" file to the index.
""")

    def check(self):
        # Check the simple branch hasn't changed.
        check_branches_identical('origin/simple', 'simple')

        result = subprocess.run(['git', 'status', '--porcelain'], stdout=subprocess.PIPE, check=True)
        status = result.stdout.decode("utf-8").strip()
        added_files = []
        untracked_files = []
        other_files = []
        for line in status.split('\n'):
            action, file_path = line.split(' ', 1)
            file_path = file_path.strip()
            if action == 'A':
                added_files.append(file_path)
            elif action == '??':
                untracked_files.append(file_path)
            else:
                other_files.append(file_path)

        if not added_files:
            raise TaskCheckException(
                'There are no paths added to the index. It should contain the "day" file.')
        if added_files and added_files != ['day']:
            raise TaskCheckException(
                'There are different paths in index that expected. It should contain only '
                'the "day" file. List of added files: %s' % ', '.join(added_files))
        if other_files:
            raise TaskCheckException(
                'There are unexpected paths in the index: %s' % ', '.join(other_files))
        if 'night' not in untracked_files:
            raise TaskCheckException(
                'The "night" file should be untracked, but is not. List of untracked '
                'files: %s' % ', '.join(untracked_files))

        print("OK")


class Commit(Task):
    branch_names = ['simple']

    def start(self):
        self.reset_branches()

        print("""
============
Task: commit
============

Switch to a branch named `simple`.

Then create a new file named "new-file" and commit it.
""")

    def check(self):
        # Check the commits count
        check_commits_count('simple', 12)

        # Check all commits from the origin/simple branch are present.
        check_old_commits_unchanged('origin/simple', 'simple')

        # Check the last commit contains only the one changed file
        result = subprocess.run(
            ['git', 'show', '--pretty=format:', '--name-only'], stdout=subprocess.PIPE, check=True
        )
        changed_files = result.stdout.decode("utf-8").strip().split('\n')
        if not changed_files:
            raise TaskCheckException(
                'The "new-file" file is not in the commit. '
                'There are no files changed by the commit.')
        if 'new-file' not in changed_files:
            raise TaskCheckException(
                'The "new-file" file is not in the commit. List of files changed by the '
                'commit: %s' % ', '.join(changed_files))
        if len(changed_files) > 1:
            raise TaskCheckException(
                'There are too many files changed by the commit: %s' % ', '.join(changed_files))

        print("OK")


class Switch(Task):
    branch_names = ['simple']

    def start(self):
        self.reset_branches()

        print("""
============
Task: switch
============

Switch to a branch named "simple".
""")

    def check(self):
        # Check current branch is "simple"
        if 'simple' != current_branch():
            raise TaskCheckException(
                'Current branch is not "simple", but "%s".' % current_branch())

        # Check the simple branch was not modified.
        check_branches_identical('origin/simple', 'simple')

        print("OK")


class Log(Task):
    branch_names = ['simple']

    def start(self):
        self.reset_branches()

        print("""
=========
Task: log
=========

In a branch `simple`, who made the last but one commit?

What is the summary of the last but one commit?

What is the second changed line in the last but one commit?
""")

    def check(self):
        answer = input("In a branch `simple`, who made the last but one commit? ")
        if answer.strip() != "Alice":
            raise TaskCheckException('This is not the correct answer.')
        answer = input("In a branch `simple`, what is the summary of the last but one commit? ")
        if answer.strip() != "Add pictures to explain merge and rebase":
            raise TaskCheckException('This is not the correct answer.')
        answer = input("In a branch `simple`, what is the second changed line in the last but one commit? ")
        if answer.strip() != "- Before merge:":
            raise TaskCheckException('This is not the correct answer.')
        print("OK")


class Diff(Task):
    branch_names = ['diff-one', 'diff-two']

    def start(self):
        self.reset_branches()

        print("""
==========
Task: diff
==========

What is the difference between `diff-one` and `diff-two` branches?
""")

    def check(self):
        answer = input("Which branch contains additional line? ")
        if answer.strip() != "diff-one":
            raise TaskCheckException('This is not the correct answer.')
        answer = input("What is the added line? ")
        if answer.strip() != "- git log     - show commit logs":
            raise TaskCheckException('This is not the correct answer.')
        print("OK")


class DeleteBranch(Task):
    branch_names = ['delete-branch-main']

    def start(self):
        self.reset_branches()

        print("""
===================
Task: delete-branch
===================

Delete branch named `delete-branch-main`.
""")

    def check(self):
        if 'delete-branch-main' in branch_list():
            raise TaskCheckException('The branch `delete-branch-main` still exists.')

        print("OK")


def main():
    # Define tasks:
    task_classes = {
        'switch': Switch,
        'add': Add,
        'commit': Commit,
        'log': Log,
        'diff': Diff,
        'new-branch': NewBranch,
        'delete-branch': DeleteBranch,
        'merge': Merge,
        'rebase': Rebase,
        'conflict-rebase': ConflictRebase,
        'commit-amend': CommitAmend,
        'reset-hard': ResetHard,
        'reset-soft': ResetSoft,
        'revert': Revert,
        'conflict-revert': ConflictRevert,
        'cherry-pick': CherryPick,
        'conflict-cherry-pick': ConflictCherryPick,
        'change-message': ChangeMessage,
        'squash-commits': SquashCommit,
        'reorganize-commits': ReorganizeCommits,
        'drop': Drop,
        'stash': Stash,
        'apply-stash': ApplyStash,
        'blame': Blame,
    }

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, epilog="List of tasks: \n  %s" % '\n  '.join(task_classes.keys()))
    parser.add_argument('taskname', help='Name of a task')
    parser.add_argument('command', choices=['start', 'check'], help='Command to run')
    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])

    if args.taskname not in task_classes:
        raise TaskException('Task "%s" not found.' % args.taskname)

    task = task_classes[args.taskname]()
    func = getattr(task, args.command, None)
    if not callable(func):
        raise TaskException(
            'Command "%s" for task "%s" not found.' % (args.command, args.taskname)
        )
    func()


if __name__ == "__main__":
    try:
        main()
    except TaskException as e:
        print(e)
        sys.exit(1)
