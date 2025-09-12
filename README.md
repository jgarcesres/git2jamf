# git2jamf [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
This action grabs the github repository (or any subdfolder of your choice) scans it for scripts and will create or update those scripts in jamf.

It starts by comparing filename of the github script (without the extension) against the name of the script in jamf:
* If it doesn't exist, it will create it
* if it exists, it will compare the hash of the body of both scripts and update it in jamf if they differ. Github is always treated as the source.
* If enabled, it will add a prefix with the `branch name_`  to a script. 

After creating and updating scripts, if enabled, it can delete any leftover script that is not found in github, thus keeping Github as your one source.

## Features
* ✅ **Script Management**: Create, update and delete scripts in Jamf from your GitHub repository
* ✅ **Extension Attribute Scripts**: Support for extension attribute scripts with dedicated folder separation
* ✅ **Branch Prefixing**: Optional branch name prefixing for test/staging workflows
* ✅ **Duplicate Detection**: Automatic detection and prevention of duplicate script names
* ✅ **Smart Sync**: Hash-based comparison to only update scripts that have actually changed

## Future state  
* slack notifications
* suggestions are welcome!

## Inputs
### `jamf_url`

**Required** the url of your jamf instance

### `jamf_auth_type`

**Optional** Defaults to `auth` but can be set to `oauth` to use `client_id` and `client_secret` instead of a username and password.

### `jamf_username`

**Required** the username to auth against jamf. If `auth_type` is set to `oauth`, this is the `client_id` . **This user should have permission to update and create scripts.**

### `jamf_password`

**Required** password for the user. If `auth_type` is set to `oauth`, this is the `client_secret`

### `script_dir`

**optional** the directory where the scripts to upload will be, this could be a subdirectoy in your repository `path/to/scripts`. By default it will try to sync all .sh and .py files from the repo, so it's **greatly recommended to provide this input**,  you can look for multiple subdirectories that share the same name, just provide a name like `**/scripts`

### `ea_script_dir`

**optional** the directory where extension attribute scripts are located, this should be separate from your regular scripts directory. By default this is `false` (disabled). When enabled, these scripts will be created/updated as extension attributes in Jamf Pro instead of regular scripts. **Important**: Extension attribute scripts will be automatically excluded from regular script processing to prevent conflicts.

### `script_extensions`

**optional** the extensions for the types of files we'll be searching for. By default it tries to look for `*.sh and *.py` files. To change the behavior, separate each extension with spaces and no periods. ie `sh py ps1`. This setting applies to both regular scripts and extension attribute scripts.

### `delete`

**optional** by default this will be `false`, if enabled it will delete any scripts that are not found in the github folder you're syncing. **Don't enable this and the prefix at the same time if you're running multiple workflows, they're not compatible**

### `prefix`

**optional** by default this will be `false`, it will add the branch name as a prefix to the script before uploading it. 

## Outputs

### `results`

what scripts were updated


## Getting started.
* First, you'll want to create the secrets that will be needed for this to work. You can do this in the settings of your repository, you'll reference those secrets in the workflow file. 
* Now create the workflow file in `.github/workflows/git2jamf.yml`
* You can use the example bellow as a basis(replace the secret values for the names of the ones you created). 
* In this example, the action runs only when a push is sent to main and it's attempting to sync a folder called `scripts` at the root of the repository. 
* You can customize it further using githubs [workflow documentation](https://help.github.com/en/actions/reference/workflow-syntax-for-github-actions)

**NOTE**: If possible, I recommend running this on a test instance first. If you can't, then try syncing just one folder with a small set of scripts so you can get a feel for how it works.

```yaml
name: git2jamf
on:
  push:
    branches: 
      - main
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: git2jamf
    steps:
      - name: checkout
        uses: actions/checkout@v3
      - name: git2jamf
        uses: jgarcesres/git2jamf@main
        with: 
          jamf_url: ${{ secrets.jamf_test_url }}
          jamf_username: ${{ secrets.jamf_test_username }}
          jamf_password: ${{ secrets.jamf_test_password }}
          script_dir: 'scripts'
```

## Example usage with extension attributes

If you want to sync both regular scripts and extension attribute scripts, you can specify separate directories for each:

```yaml
name: git2jamf
on:
  push:
    branches: 
      - main
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: git2jamf
    steps:
      - name: checkout
        uses: actions/checkout@v3
      - name: git2jamf
        uses: jgarcesres/git2jamf@main
        with: 
          jamf_url: ${{ secrets.jamf_url }}
          jamf_username: ${{ secrets.jamf_username }}
          jamf_password: ${{ secrets.jamf_password }}
          script_dir: 'scripts'
          ea_script_dir: 'extension-attributes'
```

In this setup:
- Regular scripts go in the `scripts/` directory and become Jamf Pro scripts
- Extension attribute scripts go in the `extension-attributes/` directory and become Jamf Pro extension attributes
- The two directories are processed separately to prevent conflicts


## Example usage with 2 instances
you would probably have 2 sets of secrets, with url and credentials for each instance(or share the same user creds across both servers). You also will need 2 workflow files: one for pushes to the main branch and another that goes to test. 

```yaml
name: git2jamf_test
on:
  pull_request:
    branches:
      - main
  push:
    branches: 
      - test*
      - dev*
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: git2jgit2jamf_testamf
    steps:
      - name: checkout
        uses: actions/checkout@v3
      - name: git2jamf_test 
        uses: jgarcesres/git2jamf@main
        with: 
          jamf_url: ${{ secrets.jamf_test_url }}
          jamf_username: ${{ secrets.jamf_test_username }}
          jamf_password: ${{ secrets.jamf_test_password }}
          script_dir: '**/scripts'
```
```yaml
name: git2jamf
on:
  push:
    branches: 
      - main
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: git2jamf
    steps:
      - name: checkout
        uses: actions/checkout@v3
      - name: git2jamf
        uses: jgarcesres/git2jamf@main
        with: 
          jamf_url: ${{ secrets.jamf_prod_url }}
          jamf_username: ${{ secrets.jamf_prod_username }}
          jamf_password: ${{ secrets.jamf_prod_password }}
          script_dir: '**/scripts'
```


## Example usage with one instance
The prefix remains enabled for the test branch. This might create a bit of "garbage" as the scripts that have a prefix won't be deleted automatically. 

```yaml
name: git2jamf_test
on:
  push:
    branches: 
      - test
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: git2jamf_test
    steps:
      - name: checkout
        uses: actions/checkout@v3
      - name: git2jamf_test
        uses: jgarcesres/git2jamf@main
        with: 
          jamf_url: ${{ secrets.jamf_url }}
          jamf_username: ${{ secrets.jamf_username }}
          jamf_password: ${{ secrets.jamf_password }}
          script_dir: toplevelfolder/scripts
          enable_prefix: true
```  
```yaml
name: git2jamf
on:
  push:
    branches: 
      - main
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: git2jamf
    steps:
      - name: checkout
        uses: actions/checkout@v3
      - name: git2jamf
        uses: jgarcesres/git2jamf@main
        with: 
          jamf_url: ${{ secrets.jamf_url }}
          jamf_username: ${{ secrets.jamf_username }}
          jamf_password: ${{ secrets.jamf_password }}
          script_dir: toplevelfolder/scripts
```

## Troubleshooting

### Extension Attribute API Issues

If you encounter errors related to extension attributes such as "Extension attributes endpoint not found", this may indicate:

1. **API Endpoint Compatibility**: The extension attribute API endpoints may vary between Jamf Pro versions. The current implementation uses `/uapi/v1/computer-extension-attributes` which should work with newer Jamf Pro versions.

2. **Jamf Pro Version**: Extension attribute support in the Jamf Pro API was added in later versions. Ensure your Jamf Pro instance supports extension attributes in the modern API.

3. **Permissions**: Verify that your API user has the necessary permissions to read, create, and update computer extension attributes.

If you encounter API endpoint issues, please:
- Check your Jamf Pro version and API documentation
- Verify your user has extension attribute permissions
- Consider filing an issue with details about your Jamf Pro version and the specific error messages

### Directory Structure

Make sure your directory structure separates regular scripts from extension attribute scripts:

```
your-repo/
├── scripts/              # Regular Jamf Pro scripts
│   ├── install_app.sh
│   └── configure_system.py
└── extension-attributes/  # Extension attribute scripts  
    ├── check_app_version.sh
    └── get_system_info.py
```


