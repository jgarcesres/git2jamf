# git2jamf GitHub Action

git2jamf is a Python-based GitHub Action that synchronizes scripts from a GitHub repository to Jamf Pro instances. It creates, updates, and optionally deletes scripts in Jamf based on the contents of your repository.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Setup
Always run these commands to set up the development environment:

```bash
cd /home/runner/work/git2jamf/git2jamf
python3 --version  # Verify Python 3.x is available
pip3 install -r requirements.txt  # Takes ~5 seconds
pip3 install flake8  # Takes ~2 seconds for linting
```

### Build and Test
- **Python Dependencies**: `pip3 install -r requirements.txt` -- takes 5 seconds
- **Linting**: 
  - `python3 -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics` -- takes <1 second (strict syntax check)
  - `python3 -m flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics` -- takes <1 second (full style check)
- **Docker Build**: `docker build -t git2jamf-test .` -- **OFTEN FAILS** in sandboxed environments due to network connectivity issues. NEVER CANCEL - may take 10+ minutes. Set timeout to 15+ minutes.

### Running the Action
- **Test Execution**: `python3 action.py` -- will fail with environment variable errors (expected behavior)
- **Test with Mock Variables**: 
  ```bash
  env INPUT_JAMF_AUTH_TYPE=auth INPUT_SCRIPT_EXTENSIONS="sh py" \
      INPUT_JAMF_URL=https://test.jamfcloud.com INPUT_JAMF_USERNAME=test \
      INPUT_JAMF_PASSWORD=test INPUT_SCRIPT_DIR=/tmp python3 action.py
  ```
  This will fail when trying to connect to Jamf (expected - validates script execution flow)

## Validation
- **ALWAYS** run `python3 -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics` before making changes
- **ALWAYS** run `python3 action.py` after code changes to ensure basic execution works
- The current codebase has 87 style violations but no syntax errors
- **CRITICAL**: Docker builds may fail in sandboxed environments - use local Python development instead
- No unit tests exist - validation is primarily through linting and basic execution testing

## Common Tasks

### Development Workflow
1. Make code changes to `action.py`
2. Run linting: `python3 -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`
3. Test basic execution: `python3 action.py` (should fail with env var error)
4. Fix any syntax errors found by linting
5. **DO NOT** try to fix all 87 style violations unless specifically requested

### Repository Structure
```
.
├── action.py              # Main Python script (351 lines)
├── action.yml            # GitHub Action metadata
├── Dockerfile            # Container definition (Python 3.7-alpine)
├── requirements.txt      # Python dependencies: requests, jmespath, loguru
├── README.md             # Comprehensive documentation
├── ea_script_template.xml # Extension Attribute template
├── .github/
│   ├── workflows/
│   │   └── pythonapp.yml # CI workflow with flake8 linting
│   └── ISSUE_TEMPLATE/   # Bug report and feature request templates
└── .gitignore
```

### Key Environment Variables (for understanding action.py)
The action expects these environment variables:
- `INPUT_JAMF_URL`: Jamf Pro instance URL
- `INPUT_JAMF_USERNAME`: Username or OAuth client_id
- `INPUT_JAMF_PASSWORD`: Password or OAuth client_secret
- `INPUT_JAMF_AUTH_TYPE`: "auth" or "oauth" (default: "auth")
- `INPUT_SCRIPT_DIR`: Directory containing scripts (default: workspace)
- `INPUT_SCRIPT_EXTENSIONS`: File extensions to process (default: "sh py")
- `INPUT_PREFIX`: Add branch name as prefix (default: false)
- `INPUT_DELETE`: Delete scripts not in GitHub (default: false)

### Code Quality Notes
- The current code has significant style issues but no syntax errors
- Main function `push_scripts()` is marked as too complex (complexity 12)
- Several unused variables exist (`headers` variables)
- Many whitespace and formatting issues
- **DO NOT** automatically fix all style issues unless specifically requested

### Docker Build Limitations
- **CRITICAL**: Docker builds often fail in sandboxed environments due to network issues
- Use local Python development instead of Docker for testing
- When Docker build fails, document as "Docker build fails in this environment due to network limitations"
- Expected error: "Network unreachable" when downloading pip packages

### Timing Expectations
- Dependency installation: 5 seconds
- Linting: <1 second  
- Basic script execution: <1 second
- Docker build: 10+ minutes (often fails) - NEVER CANCEL

### Troubleshooting
- If `python3 action.py` fails immediately with AttributeError about 'split', this is expected (missing environment variables)
- If Docker build fails with network errors, use local Python development
- If flake8 command not found, use `python3 -m flake8` instead
- The action requires valid Jamf Pro credentials to function fully