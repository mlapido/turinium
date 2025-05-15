#!/bin/bash
set -e

VERSION=$(grep "__version__" your_package_dir/__init__.py | cut -d"'" -f2)
TAG="v$VERSION"

echo "🛈 Extracted version: $VERSION"
echo "🛈 Checking if tag '$TAG' already exists..."

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "✅ Tag $TAG already exists. Skipping tagging."
else
  echo "🏷️ Creating tag $TAG..."
  git tag "$TAG"
  git push origin "$TAG"
  echo "✅ Tag $TAG created and pushed!"
fi