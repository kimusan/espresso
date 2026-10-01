# Release & Packaging Guide

This guide details how releases are published to **PyPI** and how multi-platform standalone release packages are generated and distributed.

---

## 📦 Package Distribution Formats

Espresso distributes packages in multiple formats to meet different user needs:

| Package Format | Target Platform | Requirements | Installation / Usage |
| :--- | :--- | :--- | :--- |
| **PyPI Wheel & sdist** (`espressoTUI`) | Universal | Python 3.10+ | `pip install espressoTUI` |
| **Universal Zipapp** (`espresso.pyz`) | Linux, macOS, BSD, Windows | Python 3.10+ | Zero installation. Just run `./espresso.pyz` |
| **Native Standalone Binary** (`espresso-linux-x86_64`) | Linux x86_64 | None (Self-contained) | `chmod +x espresso-linux-x86_64 && ./espresso-linux-x86_64` |
| **Native Standalone Binary** (`espresso-macos-arm64`) | macOS Apple Silicon (M1/M2/M3) | None (Self-contained) | `./espresso-macos-arm64` |
| **Native Standalone Binary** (`espresso-macos-x86_64`) | macOS Intel | None (Self-contained) | `./espresso-macos-x86_64` |
| **Native Standalone Binary** (`espresso-windows-x86_64.exe`)| Windows x86_64 | None (Self-contained) | `.\espresso-windows-x86_64.exe` |

---

## 🔑 PyPI Trusted Publishing Setup

Espresso uses **PyPI Trusted Publishing (OIDC)**, which eliminates the need to store long-lived API tokens in repository secrets.

### How to configure Trusted Publishing on PyPI:
1. Log in to your account at [pypi.org](https://pypi.org).
2. Go to your project settings for **`espressoTUI`** (or go to **Account Settings** -> **Publishing** if the package is newly registered).
3. Under **Add a publisher**, choose **GitHub**:
   - **PyPI Project Name**: `espressoTUI`
   - **Owner**: `kimusan`
   - **Repository name**: `espresso`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
4. Click **Add**.

*Once configured, GitHub Actions authenticates directly via short-lived OIDC tokens. Zero secrets required.*

---

## 🚀 How to Cut a New Release

### Option A: Using the Automated Release Helper (Recommended)
Espresso includes an interactive release script that runs tests, bumps the version, creates the chore commit, and creates the tag automatically:

```bash
# Preview changelog release notes ahead of time without making changes:
./scripts/release.py --preview-changelog patch

# Preview release pipeline (dry run)
./scripts/release.py --dry-run patch

# Release a patch (e.g. 0.2.0 -> 0.2.1)
./scripts/release.py patch

# Release a minor version (e.g. 0.2.0 -> 0.3.0)
./scripts/release.py minor

# Release an explicit version and automatically push:
./scripts/release.py --push 0.3.0

# Headless / plain CLI mode (for scripts or CI):
./scripts/release.py --cli patch
```

The script will:
1. Verify git working directory is clean.
2. Verify release tag is available.
3. Ensure the full test suite passes.
4. Update `src/espresso/__init__.py`.
5. Parse git history and update `CHANGELOG.md` (Keep a Changelog format with categorized Conventional Commits).
6. Create the git chore commit: `chore(release): bump version to vX.Y.Z`.
7. Create the annotated git tag: `vX.Y.Z`.
8. Prompt you to push (or print the exact push/rollback commands).

---

### Option B: Manual Release
If you prefer running commands manually:

1. **Bump Version**: Update `__version__ = "X.Y.Z"` in [`src/espresso/__init__.py`](../src/espresso/__init__.py).
2. **Commit**:
   ```bash
   git commit -am "chore(release): bump version to vX.Y.Z"
   ```
3. **Tag**:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   ```
4. **Push**:
   ```bash
   git push origin main
   git push origin vX.Y.Z
   ```

---

### 3. Automated GitHub Actions Pipeline
Once the tag is pushed to GitHub, the `.github/workflows/release.yml` pipeline triggers automatically:
1. **Tests**: Validates all tests across Python 3.10, 3.11, 3.12, 3.13.
2. **PyPI Build**: Packages `.tar.gz` and `.whl` and validates with `twine check`.
3. **Zipapp Build**: Packages universal `espresso.pyz`.
4. **Binary Compilation**: Builds standalone native executables for Linux, macOS (Apple Silicon + Intel), and Windows via PyInstaller.
5. **PyPI Publish**: Uploads packages to PyPI automatically.
6. **GitHub Release**: Attaches all 6 distribution packages plus cryptographic `SHA256SUMS` to the GitHub release.

---

## 🧪 Dry-Run & Manual Testing

Maintainers can trigger a dry-run build at any time without uploading to PyPI:
1. Navigate to **Actions** -> **Release & Publish** in the GitHub repository.
2. Click **Run workflow**.
3. Check the **Dry run** checkbox.
4. The workflow will run tests, compile all packages, and verify their integrity without publishing to PyPI.

---

## 🛡️ Verifying Release Integrity

All GitHub releases include a `SHA256SUMS` manifest:

```bash
# Verify checksums on Linux / macOS:
sha256sum -c SHA256SUMS --ignore-missing
```
