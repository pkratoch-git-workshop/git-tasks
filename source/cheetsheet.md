Git Cheatsheet
==============

Basic commands
--------------

- git add     - add file contents to the index
- git commit  - record changes to the repository

```
 +-----------+          +---------+             +------------+
 |  working  | -------> | staging | ----------> | repository |
 | directory | git add  |  area   | git commit  |            |
 +-----------+          +---------+             +------------+
```


Viewing changes
---------------

- git status  - show the working tree status
- git log     - show commit logs
- git show    - show various types of objects


Branches
--------

- git branch   - list, create, or delete branches
- git checkout - switch branches or restore working tree files
- git merge    - join two or more development histories together
- git rebase   - reapply commits on top of another base tip


Remote repositories
-------------------

- git push    - update remote refs along with associated objects
- git fetch   - doload objects and refs from another repository

