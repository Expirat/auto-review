from github import Github

# Replace 'your_personal_access_token' with your actual token
g = Github("your_personal_access_token")

def get_pull_requests(owner, repo_name):
    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
        pulls = repo.get_pulls(state='open', sort='created', direction='desc')
        for pr in pulls[:10]:
            print(f"PR #{pr.number}: {pr.title} by {pr.user.login} - {pr.state}")
        return pulls
    except Exception as e:
        print(f"Error fetching pull requests: {e}")

# Usage
get_pull_requests("your-github-username-test", "your-repo-name-test")
