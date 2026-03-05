# Release Process for Pynt

This document describes how to prepare and release new versions of Pynt (both backend and extension).

## Versioning Scheme

Pynt uses [Semantic Versioning](https://semver.org/):

- **MAJOR** (0.2.0 → 1.0.0) — Breaking API changes
- **MINOR** (0.2.0 → 0.3.0) — New features, backward compatible
- **PATCH** (0.2.0 → 0.2.1) — Bug fixes

## Pre-Release Checklist

### 1. Prepare Changes

```bash
# Ensure working directory is clean
git status

# Update version numbers
# - server/main.py (if version constant exists)
# - pyproject.toml (project.version)
# - extension/package.json (version)

# Keep them in sync!
```

### 2. Run Full Test Suite

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Verify code quality
make format-check
make lint
make typecheck
```

### 3. Update Documentation

- **README.md** — Update if features changed
- **CHANGELOG.md** — Document what's new, fixed, breaking
- **API DOCS** — If endpoints changed, update README

Example CHANGELOG entry:

```markdown
## [0.2.1] - 2024-03-05

### Added
- RAG evaluation tests with RAGAS metrics
- `pytest-timeout` dependency for test robustness

### Fixed
- LLM timeout handling in agents
- False positive detection in security analysis

### Changed
- Updated langchain-groq to 1.1.1
- Improved RAG context truncation logic

### Breaking Changes
- None in this release
```

### 4. Create Release Branch

```bash
git checkout -b release/v0.2.1
```

## Backend Release (Python Package)

### 1. Build Package

```bash
make clean
make build

# Verify dist/ contains:
# - pynt-server-0.2.1.tar.gz
# - pynt-server-0.2.1-py3-none-any.whl
```

### 2. Test Installation

```bash
# Fresh virtual environment
python -m venv test_env
source test_env/bin/activate

# Install from local wheel
pip install dist/pynt-server-0.2.1-py3-none-any.whl

# Quick sanity check
python -c "from server.main import app; print('✓ Import successful')"

deactivate
rm -rf test_env
```

### 3. Publish to PyPI (Optional)

```bash
# Requires PyPI account (https://pypi.org/account/register/)
# And credentials in ~/.pypirc

pip install twine

# Check package metadata
twine check dist/*

# Upload to PyPI test environment first
twine upload --repository testpypi dist/*

# Verify at https://test.pypi.org/project/pynt-server/

# Then upload to production
twine upload dist/*
```

## Extension Release (VS Code)

### 1. Publish Extension

Prerequisites:
```bash
npm install -g @vscode/vsce
```

### 2. Prepare Extension

```bash
cd extension

# Build
npm run compile
npm run lint

# Ensure no errors
npm test  # if tests exist

# Package as .vsix
npx @vscode/vsce package

# Creates: pynt-0.2.1.vsix
```

### 3. Publish to VS Code Marketplace

Option A: **Manual Upload**
1. Go to https://marketplace.visualstudio.com/manage/createpublisher
2. Create publisher (if needed)
3. Visit https://marketplace.visualstudio.com/manage/publishers
4. Click "Create Extension" → Upload `.vsix` file

Option B: **Automated with VSCE**

```bash
# Update personal access token at ~/.vscode/vce-token
vsce login your-publisher-name

# Publish
vsce publish patch  # Auto-increments patch version
# or
vsce publish 0.2.1   # Specific version
```

## Docker Image Release

```bash
# Build and tag
docker build -t pynt:0.2.1 -t pynt:latest .

# Push to registry (if using)
docker push pynt:0.2.1
docker push pynt:latest
```

## Final Release Steps

### 1. Commit and Tag

```bash
git add .
git commit -m "Release v0.2.1

- RAG evaluation with RAGAS
- Improved timeout handling
- Updated dependencies

See CHANGELOG.md for details"

# Create annotated tag (preferred)
git tag -a v0.2.1 -m "Release version 0.2.1"

# Push
git push origin release/v0.2.1
git push origin v0.2.1
```

### 2. Create GitHub Release

1. Go to repository → Releases → "Create a new release"
2. Tag: `v0.2.1`
3. Title: `Pynt v0.2.1`
4. Description: (copy from CHANGELOG)
5. Attach artifacts:
   - `dist/pynt-server-0.2.1.tar.gz`
   - `dist/pynt-server-0.2.1-py3-none-any.whl`
   - `extension/pynt-0.2.1.vsix`
6. Click "Publish release"

### 3. Merge PR and Update Main

```bash
# Create PR from release/v0.2.1 to main
git push origin release/v0.2.1

# After merge, update develop
git checkout develop
git pull origin main
git push origin develop
```

### 4. Announce Release

- Update project website (if exists)
- Post in community channels
- Send email to subscribers (if applicable)

## Hotfix Release Process (0.2.1 → 0.2.2)

For critical bug fixes only:

```bash
# Branch from tag
git checkout -b hotfix/v0.2.2 v0.2.1

# Fix bug
git add .
git commit -m "Fix: [bug description]"

# Build & test
make test

# Release
git tag -a v0.2.2 -m "Hotfix: [description]"
git push origin hotfix/v0.2.2 v0.2.2

# Merge back to main AND develop
git checkout main
git merge hotfix/v0.2.2
git push origin main

git checkout develop
git merge hotfix/v0.2.2
git push origin develop
```

## Post-Release

### 1. Update Development Version

```bash
# Prepare for next version
# pyproject.toml: 0.2.1 → 0.2.2-dev
# extension/package.json: 0.2.1 → 0.2.2-dev

git add .
git commit -m "Bump version to 0.2.2-dev"
git push origin develop
```

### 2. Monitor Feedback

- Watch GitHub issues for bug reports
- Monitor extension rating on VS Code Marketplace
- Respond to user feedback

### 3. Document Lessons Learned

If anything went wrong during release:
- Update this process document
- Create tickets for improvements
- Share with team

## Troubleshooting

### Extension not updating in VS Code?

```bash
# Increment version in package.json
# Rebuild
npm run compile

# Republish with higher version
vsce publish 0.2.2
```

### PyPI Upload Failed?

```bash
# Check credentials
cat ~/.pypirc

# Try again with verbose output
twine upload -r pypi --verbose dist/*
```

### Git Tag Already Exists?

```bash
# Delete local tag
git tag -d v0.2.1

# Delete remote tag
git push origin --delete v0.2.1

# Create new tag
git tag -a v0.2.1 -m "Release v0.2.1"
git push origin v0.2.1
```

## Checklist for Release

- [ ] All tests pass (`make test`)
- [ ] Code quality passes (`make lint`, `make format-check`, `make typecheck`)
- [ ] Version numbers consistent (pyproject.toml, package.json, CHANGELOG.md)
- [ ] CHANGELOG.md updated
- [ ] README.md updated if needed
- [ ] Backend package builds (`make build`)
- [ ] Backend installation tested
- [ ] Extension compiles (`make build-extension`)
- [ ] Extension packaged (`.vsix` file created)
- [ ] Release commit created with tag
- [ ] GitHub release created with artifacts
- [ ] Extension published to VS Code Marketplace
- [ ] PyPI package published (if applicable)
- [ ] Post-release version bumped to -dev
- [ ] Announcement sent (if applicable)

---

**Release successfully completed! 🎉**
