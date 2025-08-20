
# Development Workflow

## Development

- Work on features in separate feature branches
- Create PRs to merge into dev
-Test and integrate on the dev branch

## Release Preparation

- Create a PR from dev to main when ready for a release
- Update version in pyproject.toml
- Update CHANGELOG.md
- Get the PR reviewed and approved

## Release

- Merge the approved PR to main
- Create and push a tag that matches the version:

```bash
Run
git checkout main
git pull
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

This will trigger the GitHub Action to build and publish to PyPI

## Benefits of This Approach

- Quality Control: All changes to main go through PR review
- Clear Release Process: Releases are explicitly triggered by tags
- Version Consistency: The tag must match the version in pyproject.toml
- Automation: Publishing happens automatically when tagged

## Additional Recommendations

- Semantic Versioning: Follow [SemVer](https://semver.org) for your version numbers
- Changelog: Maintain a CHANGELOG.md file to track changes
- Pre-commit Hooks: Set up pre-commit hooks for linting and formatting
- Automated Testing: Set up GitHub Actions for running tests on PRs

# Change Log

2025-08-20 Added publishing

