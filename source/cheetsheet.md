Git Cheatsheet
==============

Basic commands
--------------

| Command     | Description                        |
| ----------- | ---------------------------------- |
| git add     | add file contents to the index     |
| git commit  | record changes to the repository   |

```
 +-----------+          +---------+             +------------+
 |  working  | -------> | staging | ----------> | repository |
 | directory | git add  |  area   | git commit  |            |
 +-----------+          +---------+             +------------+
```


Viewing changes
---------------

| Command     | Description                        |
| ----------- | ---------------------------------- |
| git status  | show the working tree status       |
| git log     | show commit logs                   |
| git show    | show various types of objects      |


Branches
--------

| Command      | Description                                       |
| ------------ | ------------------------------------------------- |
| git branch   | list, create, or delete branches                  |
| git checkout | switch branches or restore working tree files     |
| git merge    | join two or more development histories together   |

  - Before merge:
```
            A---B---C topic
           /
      D---E---F---G master
```

  - After merge:
```
            A---B---C topic
           /         \
      D---E---F---G---H master
```

| Command      | Description                                       |
| ------------ | ------------------------------------------------- |
| git rebase   | reapply commits on top of another base tip        |

  - Before rebase:
```
            A---B---C topic
           /
      D---E---F---G master
```

  - After rebase:
```
                    A'--B'--C' topic
                   /
      D---E---F---G master
```


Remote repositories
-------------------

| Command     | Description                                        |
| ----------- | -------------------------------------------------- |
| git push    | update remote refs along with associated objects   |
| git fetch   | doload objects and refs from another repository    |

