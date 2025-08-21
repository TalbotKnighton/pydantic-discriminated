#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Check if a version argument was provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 v0.1.1"
    exit 1
fi

VERSION=$1
VERSION_NO_V="${VERSION#v}"  # Remove the 'v' prefix for use in pyproject.toml

# Validate version format
if ! [[ $VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must be in format vX.Y.Z (e.g., v0.1.1)"
    exit 1
fi

# Ensure we're on the dev branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "dev" ]; then
    echo "Error: You must be on the dev branch to publish a new version"
    exit 1
fi

# Make sure test output files are in .gitignore
if ! grep -q "discriminator_tests.json" .gitignore 2>/dev/null; then
    echo "Adding test output files to .gitignore..."
    cat >> .gitignore << EOF
# Test output files
discriminator_tests.json
discriminator_tests.log
.coverage
coverage.xml
EOF
    git add .gitignore
    git commit -m "Add test output files to .gitignore"
    echo "Updated .gitignore and committed changes."
fi

# Clean up any test output files that might interfere with branch switching
echo "Cleaning up test output files..."
rm -f discriminator_tests.json discriminator_tests.log .coverage coverage.xml

# Make sure the working directory is clean (except for ignored files)
if ! git diff-index --quiet HEAD --; then
    echo "Error: Working directory has uncommitted changes"
    exit 1
fi

# Pull the latest changes from the dev branch
echo "Pulling latest changes from dev branch..."
git pull origin dev

# Run unit tests before proceeding
echo "Running unit tests..."
echo "Installing package with development dependencies..."
pip install -e ".[dev]"  # Install the package with dev dependencies

if ! python -m pytest; then
    echo "Error: Tests failed. Please fix the failing tests before publishing."
    exit 1
fi
echo "All tests passed successfully!"

# Clean up test output files again
echo "Cleaning up test output files..."
rm -f discriminator_tests.json discriminator_tests.log .coverage coverage.xml

# Update version in pyproject.toml
echo "Updating version in pyproject.toml to $VERSION_NO_V..."
sed -i.bak "s/^version = \".*\"/version = \"$VERSION_NO_V\"/" pyproject.toml
rm pyproject.toml.bak  # Remove backup file

# Update version in __init__.py (accounting for src layout)
INIT_PATH="src/pydantic_discriminated/__init__.py"
if [ -f "$INIT_PATH" ]; then
    if grep -q "__version__" "$INIT_PATH"; then
        # Update existing version
        echo "Updating version in $INIT_PATH..."
        sed -i.bak "s/__version__ = \".*\"/__version__ = \"$VERSION_NO_V\"/" "$INIT_PATH"
    else
        # Add version if it doesn't exist
        echo "Adding version to $INIT_PATH..."
        echo "" >> "$INIT_PATH"  # Add a newline
        echo "__version__ = \"$VERSION_NO_V\"" >> "$INIT_PATH"
    fi
    rm -f "${INIT_PATH}.bak"  # Remove backup file if it exists
else
    echo "Warning: $INIT_PATH not found, skipping version update in __init__.py"
fi

# Update changelog if it exists
if [ -f "CHANGELOG.md" ]; then
    echo "Adding new version entry to CHANGELOG.md..."
    DATE=$(date +%Y-%m-%d)
    sed -i.bak "s/^# Changelog/# Changelog\n\n## $VERSION ($DATE)\n\n- TODO: Add release notes\n/" CHANGELOG.md
    rm CHANGELOG.md.bak  # Remove backup file
    
    # Open the changelog for editing
    echo "Opening CHANGELOG.md for editing. Please add release notes and save..."
    ${EDITOR:-vi} CHANGELOG.md
fi

# Commit the version changes
echo "Committing version changes..."
git add pyproject.toml
if [ -f "$INIT_PATH" ]; then
    git add "$INIT_PATH"
fi
if [ -f "CHANGELOG.md" ]; then
    git add CHANGELOG.md
fi
git commit -m "Bump version to $VERSION"

# Push changes to dev branch
echo "Pushing changes to dev branch..."
git push origin dev

# Build and deploy documentation locally
echo "Building and deploying documentation version $VERSION_NO_V locally..."
mike deploy $VERSION_NO_V latest --update-aliases
mike set-default latest

echo "Documentation built and deployed locally."
echo "To view the documentation locally, run: mike serve"

# Create pull request from dev to main
echo "Creating a pull request from dev to main..."
echo "Please go to GitHub and create the PR: https://github.com/TalbotKnighton/pydantic-discriminated/compare/main...dev"
echo "After the PR is reviewed and merged, run the following commands:"
echo "git checkout main"
echo "git pull origin main"
echo "git tag -a $VERSION -m \"Release $VERSION\""
echo "git push origin $VERSION"

# Ask if the PR has been merged
read -p "Has the PR been merged to main? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Clean up test output files again to ensure branch switching works
    echo "Cleaning up test output files..."
    rm -f discriminator_tests.json discriminator_tests.log .coverage coverage.xml
    
    # Switch to main and pull latest changes
    echo "Switching to main branch and pulling latest changes..."
    git checkout main
    git pull origin main
    
    # Create and push the tag
    echo "Creating and pushing tag $VERSION..."
    git tag -a $VERSION -m "Release $VERSION"
    git push origin $VERSION
    
    # # Push documentation to GitHub Pages
    # echo "Pushing documentation to GitHub Pages..."
    # mike deploy --push --update-aliases $VERSION_NO_V latest
    # mike set-default --push latest
    
    # Switch back to dev branch
    echo "Switching back to dev branch..."
    git checkout dev
    
    echo "Release process completed successfully!"
    echo "The GitHub Actions workflow should now be building and publishing your package."
    echo "Documentation has been deployed to GitHub Pages."
    echo "You can check the progress here: https://github.com/TalbotKnighton/pydantic-discriminated/actions"
else
    echo "Please complete the PR process and then run:"
    echo "git checkout main"
    echo "git pull origin main"
    echo "git tag -a $VERSION -m \"Release $VERSION\""
    echo "git push origin $VERSION"
    echo "mike deploy --push --update-aliases $VERSION_NO_V latest"
    echo "mike set-default --push latest"
    echo "git checkout dev"
fi