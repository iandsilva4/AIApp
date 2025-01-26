# Ian-s-LLM-Project

# ############ #
#    UPDATE    #
# ############ #

# 6. Create a new branch for your work (recommended)
git checkout -b <branch_name>

# 1. Stage the changes
git add . 

# This command adds the modified README.md file to the staging area, 
# preparing it for the next commit.

# 2. Commit the changes
git commit -m "Updated README.md with [your changes]"

# This creates a new commit with the staged changes and includes your commit 
# message describing the changes made. Replace "[your changes]" with a 
# brief and informative description.

# 3. Push the changes to the remote branch
git push origin <your_branch_name>

# This pushes your local commits to the <your_branch_name> branch on the 
# remote repository (e.g., GitHub). Replace <your_branch_name> with the 
# actual name of your branch (e.g., "feature/new-feature").

# 4. Create a Pull Request on GitHub
gh pr create [name]
gh pr merge [name]

# 5. (After the Pull Request is merged)
# Update your local 'main' branch with the merged changes:
git checkout main
git pull origin main

