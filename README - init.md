# Ian-s-LLM-Project

# ############ #
#    STARTUP   #
# ############ #

# 1. Navigate to your project directory
cd path/to/your/project 

# 2. Check the current branch (optional)
git branch
git remote add origin https://github.com/iandsilva4/iansLLMProject

# 3. Fetch changes from the remote repository
git fetch origin

# This command downloads the latest commits and references from the remote repository 
# ("origin") without merging them into your local branches. This allows you to see 
# what changes have happened on the remote without immediately modifying your local work.

# 4. Merge changes from the remote 'main' branch into your local branch
git merge origin/main

# This command merges the latest changes from the remote 'main' branch 
# into your currently checked-out branch. If there are no conflicts, the merge 
# will happen automatically. 

# 5. Check for and resolve conflicts (if any)
git status 

# This command shows the status of your working directory, including any 
# unmerged files, staged changes, and uncommitted changes. If there are 
# conflicts, git status will display messages like:
#
#   Unmerged paths:
#     (use "git add <file>..." to mark resolution)
#     both modified:      path/to/file1
#     both modified:      path/to/file2
#
# If conflicts exist:
#   - Open the conflicting files in a text editor.
#   - Identify and resolve the conflicts.
#   - Stage the resolved files: git add path/to/file1 path/to/file2
#   - Commit the merge: git commit -m "Merged changes from origin/main"

# 5B. OPTIONAL
git reset --hard origin/main 

# 6. Create a new branch for your work (recommended)
git checkout -b <branch_name>

# This creates a new branch for your development work and switches to it. 
# Working on a separate branch allows you to experiment and make changes 
# without directly affecting the 'main' branch.

# 7. You are now ready to start coding!

1/23/25 Here is an update.
1/25/25 Here is an update.