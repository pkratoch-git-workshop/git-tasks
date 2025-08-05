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

In the `cherry-pick-feature` branch, there are some commits that modified the `fame-is-a-bee.md` \
file (and then few other commits that modified the `after-great-pain.md` file). Cherry-pick into \
the `cherry-pick-main` branch only those that modified the `fame-is-a-bee.md`.

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
        check_commits_count('cherry-pick-main', 5)

        # Check the commit order
        expected_summaries = [
            'Add the name of the author of the "Fame is a bee"',
            'Finisth the poem "Fame is a bee"',
            'Add the first line',
            'Add a poem: I started Early',
            'Add a place for poems',
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

In the `conflict-cherry-pick-feature` branch, there are some commits that added the "Fame is a \
bee" poem to the `poems.md` file (and then few other commits that added another poem). Cherry-pick \
into the `conflict-cherry-pick-main` branch only those that added the "Fame is a bee" poem.

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
        check_commits_count('conflict-cherry-pick-main', 3)

        # Check the commit order
        expected_summaries = [
            'Add the "Fame is a bee" poem',
            'Add a title and author of "Fame is a bee"',
            'Create a file with poems',
        ]
        check_summaries('conflict-cherry-pick-main', expected_summaries)

        # Check the file contains the correct changes
        subprocess.run(['git', 'switch', 'conflict-cherry-pick-main'], check=True)
        with open('poems.md') as f:
            lines = [line.strip() for line in f if line.strip()]
        for line in lines:
            if line[:7] in ["=======", "<<<<<<<", ">>>>>>>"]:
                raise TaskCheckException(
                    'The conflict was not resolved, there are some conflict markings '
                    'left: %s' % line[:7]
                )
        expected_lines = [
            '# Fame is a bee',
            '*By Emily Dickinson*',
            'Fame is a bee.',
            'It has a song --',
            'It has a sting --',
            'Ah, too, it has a wing.',
        ]
        if lines != expected_lines:
            raise TaskCheckException(
                'The content of poems.md is different than expected. '
                'Expected lines (without empty lines):\n%s' % '\n'.join(expected_lines)
            )

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
            'Add a poem I started early',
            'Update the poem to the newer version',
            'Add "by" before the name of the author',
            'Add a poem: Forever is composed of nows',
            'Add the missing name of the author',
            'Add the poem The Chariot',
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
            'Fix a typo in the word "forever" in "Forever is composed of nows"',
            'Split the poem "Forever is composed by nows" correctly into lines',
            'Add a poem "I started early"',
            'Add a poem "The Chariot"',
            'Add a poem "Forever is composed of nows"',
        ]
        check_summaries('conflict-rebase-feature', expected_summaries)

        # Check the forever-is-composed-of-nows.md file is correct
        expected_start = [
            "# Forever – is composed of Nows",
            "*By Elimy Dickinson*",
            "Forever – is composed of Nows –",
            "‘Tis not a different time –",
        ]
        if current_branch() != 'conflict-rebase-feature':
            switch_branch('conflict-rebase-feature')
        with open('forever-is-composed-of-nows.md') as f:
            lines = [line.strip() for line in f if line.strip()]
        if lines[:4] != expected_start:
            raise TaskCheckException(
                'The content of forever-is-composed-of-nows.md is different than expected. '
                'It should start with (without empty lines):\n%s' % '\n'.join(expected_start)
            )

        print("OK")


class ResetHard(Task):
    branch_names = ['simple']

    def start(self):
        self.reset_branches()

        print("""
================
Task: reset-hard
================

Reset the `simple` branch to the point right before the last commit. Reset both the \
index and the working tree, i.e. completely discard all changes introduced by the commit.

If the history looks like this:

            A---B---C---D---E---F main

Then the result of resetting to commit E should look like this:

            A---B---C---D---E main
""")

    def check(self):
        # Check all commits from the origin/simple are present in simple.
        new_hexshas = commit_log('simple')
        new_summaries = commit_log('simple', FORMAT_SUMMARY)
        skip_first = True
        for hexsha in commit_log('origin/simple'):
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
        check_commits_count('simple', 7)

        # Check the commit order
        expected_summaries = [
            'Fix the name of the poem: Because I could not stop for Death',
            'Keep both versions of the poem after all',
            'Update the poem to the newer version',
            'Add "by" before the name of the author',
            'Add a poem: Forever is composed of nows',
            'Add the missing name of the author',
            'Add the poem The Chariot',
        ]
        check_summaries('simple', expected_summaries)

        print("OK")

class ResetSoft(Task):
    branch_names = ['simple']

    def start(self):
        self.reset_branches()

        print("""
================
Task: reset-soft
================

Reset the `simple` branch to the point right before the last commit, but keep the index \
and the working tree.
""")


    def check(self):
        # Check all commits from the origin/reset-soft-main are present in reset-soft-main.
        new_hexshas = commit_log('simple')
        new_summaries = commit_log('simple', FORMAT_SUMMARY)
        skip_first = True
        for hexsha in commit_log('origin/simple'):
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
        check_commits_count('simple', 7)

        # Check the commit order
        expected_summaries = [
            'Fix the name of the poem: Because I could not stop for Death',
            'Keep both versions of the poem after all',
            'Update the poem to the newer version',
            'Add "by" before the name of the author',
            'Add a poem: Forever is composed of nows',
            'Add the missing name of the author',
            'Add the poem The Chariot',
        ]
        check_summaries('simple', expected_summaries)

        diff_staged = git_diff('--staged')
        diff_resetted_commit = git_diff('origin/simple^', 'origin/simple')
        if diff_staged != diff_resetted_commit:
            raise TaskCheckException('The index is not the same as the resetted commit.')

        print("OK")


class Revert(Task):
    branch_names = ['simple']

    def start(self):
        self.reset_branches()

        print("""
============
Task: revert
============

In a branch `simple`, there is a commit with summary "Add a poem: Forever is composed of \
nows". Revert this commit.

Note that you don't want to change the history of the `simple` branch, but to create new \
commit that is opposite to the one you want to undo.

If the history looks like this:

            A---B---C---D---E---F main

Then the result should look like this:

            A---B---C---D---E---F---D' main
""")


    def check(self):
        # Check all commits from the origin/simple are present in simple.
        check_old_commits_unchanged('origin/simple', 'simple')

        # Check the commits count
        check_commits_count('simple', 9)

        # Check the commit order
        expected_summaries = [
            '<REVERT COMMIT>',
            'Add a poem I started early',
            'Fix the name of the poem: Because I could not stop for Death',
            'Keep both versions of the poem after all',
            'Update the poem to the newer version',
            'Add "by" before the name of the author',
            'Add a poem: Forever is composed of nows',
            'Add the missing name of the author',
            'Add the poem The Chariot',
        ]
        check_summaries('simple', expected_summaries, skip=1)

        # Check the last commit is the correct reverted commit by comparing diffs
        commits = commit_log('simple')
        expected_diff = git_diff(commits[7], commits[6])
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

        # Check that the commit message has been changed.
        if main_summaries[1] != expected_summaries[1]:
            raise TaskCheckException(
                'The commit message seems not be changed correctly.\nCurrent message: '
                '%s\nExpected message: %s' % (main_summaries[1], expected_summaries[1]))

        # Check summaries
        check_summaries('change-message-tasks', expected_summaries)

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
    branch_names = ["simple"]

    def start(self):
        self.reset_branches()

        print("""
==================
Task: commit-amend
==================

In the branch `simple`, the last commit adds a poem by Emily Dickinson. \
Unfortunately, one of the writers made a typo and left this mistake in the name of \
the author which is `Elimy` but should be `Emily`. Before we merge the content of this branch \
into `main`, we would like to correct the mistake before we do so.

Since this is only a minor change, do not produce an extra commit, but add the change \
to the existing commit instead.

After the change, there should be the same number of commits in the branch with the same commit \
messages as before!

""")

    def check(self):
        # Check the commits count
        check_commits_count('simple', 8)

        # Check the summaries were not changed.
        if commit_log('origin/simple', FORMAT_SUMMARY) != commit_log('simple', FORMAT_SUMMARY):
            last_original = commit_log('origin/simple', FORMAT_SUMMARY)[0]
            last_new = commit_log('simple', FORMAT_SUMMARY)[0]
            if last_original != last_new:
                raise TaskCheckException(
                    'The commit messages differ from what is expected.\nExpected commit '
                    'message: %s\nCurrent commit message: %s' % (last_original, last_new)
                )
            raise TaskCheckException('The commit messages on the branch `simple` changed.')

        # Check that there is a difference in content between the original and the new commit.
        original = commit_show('origin/simple')
        new = commit_show('simple')
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

        if main_summaries[0] != "Add my favourite poem.":
            raise TaskCheckException(
                'The message of the commit differs from what is expected.\n'
                'Expected commit message: %s\nCurrent commit message: %s' % (
                    expected_summaries[0], main_summaries[0]
                )
             )

        # Check summaries
        check_summaries('apply-stash-tasks', expected_summaries)

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

In a branch `conflict-revert-main`, revert the commit with summary "Add another poem: Fame is a bee".

Note that you don't want to change the history of the `conflict-revert-main` branch, but to \
create new commit that is opposite to the one you want to undo.

In this scenario, you will encounter a conflict and will need to resolve it (and then "git add" \
all the changes and "git revert --continue"). It is also possible that you will need to combine \
changes from both sides of the conflict!

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
        check_commits_count('conflict-revert-main', 4)

        # Check the commit order
        expected_summaries = [
            '<REVERT COMMIT>',
            'Fix typos in the name and author of the second poem',
            'Add another poem: Fame is a bee',
            'Add poems by Emily Dickinson',
        ]
        check_summaries('conflict-revert-main', expected_summaries, skip=1)

        # Check the file contains the correct changes
        subprocess.run(['git', 'switch', 'conflict-revert-main'], check=True)
        with open('poems.md') as f:
            lines = [line.strip() for line in f if line.strip()]
        for line in lines:
            if line[:7] in ["=======", "<<<<<<<", ">>>>>>>"]:
                raise TaskCheckException(
                    'The conflict was not resolved, there are some conflict markings '
                    'left: %s' % line[:7]
                )
            if line == '# Fever – is composed of Nows':
                raise TaskCheckException(
                    'The conflict was not resolved correctly: the typo that was fixed '
                    'in one of the commits is there again: # Fever – is composed of Nows'
                )
        expected_lines = [
            '# Forever – is composed of Nows',
            '*By Emily Dickinson*',
            'Forever – is composed of Nows –',
            '‘Tis not a different time –',
            'Except for Infiniteness –',
            'And Latitude of Home –',
            'From this – experienced Here –',
            'Remove the Dates – to These –',
            'Let Months dissolve in further Months –',
            'And Years – exhale in Years –',
            'Without Debate – or Pause –',
            'Or Celebrated Days –',
            'No different Our Years would be',
            'From Anno Dominies –',
        ]
        if lines != expected_lines:
            raise TaskCheckException(
                'The content of poems.md is different than expected. '
                'Expected lines (without empty lines):\n%s' % '\n'.join(expected_lines)
            )

        print("OK")


class NewBranch(Task):
    branch_names = ['simple']

    def start(self):
        self.reset_branches()
        subprocess.run(['git', 'branch', '-D', 'new-branch'])

        print("""
================
Task: new-branch
================

Create a new branch named `new-branch` starting of the `simple` branch.
""")


    def check(self):
        # Check the simple branch hasn't changed.
        check_branches_identical('origin/simple', 'simple')

        # Check branch exists.
        if 'new-branch' not in branch_list() and '* new-branch' not in branch_list():
            raise TaskCheckException('Branch "new-branch" does not exist.')

        # Check new-branch is the same as simple.
        try:
            check_branches_identical('simple', 'new-branch')
        except TaskCheckException:
            raise TaskCheckException('The new branch is not on the top of the `simple` branch.')

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
        # Check the main branch hasn't changed.
        try:
            check_branches_identical('origin/main', 'main')
        except TaskCheckException:
            raise TaskCheckException(
                'In this task, you should only add the file to the index, not create a commit. '
                'To try once more, call the `start` command again.')

        result = subprocess.run(['git', 'status', '--porcelain'], stdout=subprocess.PIPE, check=True)
        status = result.stdout.decode("utf-8").strip()
        added_files = []
        untracked_files = []
        other_files = []
        for line in status.split('\n'):
            if line:
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
        check_commits_count('simple', 9)

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

What line was added in the last but one commit?

In the check, you will be prompted for the answers to all these questions.
""")

    def check(self):
        answer = input("In a branch `simple`, who made the last but one commit? ")
        if answer.strip() not in ["Dave", "dave", "dave@example.com", "Dave <dave@example.com>"]:
            raise TaskCheckException('This is not the correct answer.')
        answer = input("In a branch `simple`, what is the summary of the last but one commit? ")
        if answer.strip() != "Fix the name of the poem: Because I could not stop for Death":
            raise TaskCheckException('This is not the correct answer.')
        answer = input("In a branch `simple`, what line was _added_ in the last but one commit? ")
        if answer.strip() != "Because I could not stop for Death":
            if answer.strip() == "+Because I could not stop for Death":
                raise TaskCheckException(
                    "Almost. The '+' sign only denotes that the line was added, "
                    "but it's not part of the added line itself."
                )
            else:
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
    branch_names = ['simple']

    def start(self):
        self.reset_branches()

        print("""
===================
Task: delete-branch
===================

Delete branch named `simple`.
""")

    def check(self):
        if 'simple' in branch_list() or '* simple' in branch_list():
            raise TaskCheckException('The branch `simple` still exists.')

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
