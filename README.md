# Git Tasks

## How to solve tasks

### Prerequisites

1. Enter the `sudo dnf install python3-GitPython` command to install necessary dependencies.
1. Before starting the first task, run `init-tasks` to make the `task.py` script available.

## Working with tasks

1. Pick a task from the list below.
1. Run a script to start a task: `python3 task.py <taskname> start`
1. Solve the task.
1. Run a script to verify your solution: `python3 task.py <taskname> check`


## Tips

All branches for given task have prefix `<taskname>-`.

To see only task-related branches in gitk: `gitk --branches=<taskname>-*`


## List of tasks

1. switch
1. add
1. commit
1. new-branch
1. merge
1. rebase
1. blame
1. stash
1. apply-stash
1. cherry-pick
1. conflict-cherry-pick
1. commit-amend
1. reset-hard
1. reset-soft
1. revert
1. conflict-revert
1. change-message
1. squash-commits
1. reorganize-commits
1. drop

