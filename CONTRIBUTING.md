# Contributing to EyeCon

Thank you for your interest in EyeCon! This guide explains how to work with pull requests and contribute to the project.

## Reviewing and Merging a Pull Request

When a pull request (PR) has been opened against this repository, follow these steps:

### 1. Open the Pull Request on GitHub

Go to the repository on GitHub and click the **"Pull requests"** tab. Select the open PR to view its details, including:
- The list of changed files
- A summary of what was changed and why
- Any automated checks (CI status)

### 2. Review the Changes

- Click **"Files changed"** to see a diff of every modified file.
- Read through the changes and leave inline comments if anything needs clarification or adjustment.
- If the changes look good, click **"Review changes"** → select **"Approve"** → click **"Submit review"**.

### 3. Merge the Pull Request

Once you are happy with the changes:

1. Scroll to the bottom of the PR page.
2. Click **"Merge pull request"** (or choose "Squash and merge" / "Rebase and merge" depending on your preference).
3. Confirm by clicking **"Confirm merge"**.
4. Optionally, click **"Delete branch"** to clean up the feature branch after merging.

> **Tip:** If you are the sole maintainer you can approve and merge your own PRs directly on GitHub.

---

## Contributing Code

### Fork & Branch

```bash
# Fork the repo on GitHub, then clone your fork
git clone https://github.com/<your-username>/EyeCon.git
cd EyeCon

# Create a feature branch
git checkout -b feature/my-improvement
```

### Make Changes and Test

```bash
# Set up the environment
python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# Run the application to verify your changes
python Main.py
```

### Open a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feature/my-improvement
   ```
2. Go to the original repository on GitHub.
3. Click **"Compare & pull request"**.
4. Fill in the title and description, then click **"Create pull request"**.

---

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code.
- Write docstrings for all public classes and functions.
- Keep commits focused — one logical change per commit.

## Reporting Bugs or Requesting Features

Please open a [GitHub Issue](https://github.com/Mordpheus/EyeCon/issues) with a clear description and, if applicable, steps to reproduce the problem.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
