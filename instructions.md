# Creating new tasks

Each task has a name `<taskname>` and is contained in branches with prefix `<taskname>-` (e.g. task `merge` in branches `merge-main` and `merge-feature`) on top of the main branch.

The main branch contains script `.task.py` that can perform a task setup (show description, checkout to branches etc.) and check a solution. (When solving the tasks, the script will be copied to `task.py`, so that it's available in all branches and git ignores it.)

To simulate different users committing to the repository, use the `switch-user.sh` script.
Copy it to your branch for convenience:
`$ git checkout how-to-create-tasks -- switch-user.sh`
`$ git restore --staged switch-user.sh`

