# git2jamf [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
This action grabs the github work directory (or any subdfolder of your choice) scans it for scripts and will create or update those scripts in jamf.

It starts by comparing filename of the github script (without the extension) against the name of the script in jamf:
* If it doesn't exist, it will create it
* if it exists, it will compare the hash of the body of both scripts and update it in jamf if they differ. Github is always treated as the source.
* If enabled, it will add a suffix with the `branch name_`  to a script. 

## Future state
I'm hoping to add the ability to delete scripts and to handle extension attributes. Suggestions are welcome!

## Inputs
### `jamf_url`

**Required** the url of your jamf instance

### `jamf_username`

**Required** the username to auth against jamf. **This user should have permission to update and create scripts.**

### `jamf_password`

**Required** password for the user

### `script_dir`

**optional** the directory where the scripts to upload will be, this could be a subdirectoy in your repository `path/to/scripts`. By default it will try to sync all .sh and .py files from the repo, so it's **greatly recommended to provide this input**,  you can look for multiple subdirectories that share the same name, just provide a name like `**/scripts`

### `script_extensions`

**optional** the extensions for the types of files we'll be searching for. By default it tries to look for `*.sh and *.py` files. To change the behavior, separate each extension with spaces and no periods. ie `sh py ps1`

### `prefix`

**optional** by default this will be `false`, it will add the branch name as a prefix to the script before uploading it. 

## Outputs

### `results`

what scripts were updated


## Getting started.
If possible, I recommend running this on a test instance first. If you can't, then try syncing just one folder with a small set of scripts so you can get a feel for how it works. First, you'll want to create the secrets that will be needed for this to work. You can do this in the settings of your repository, you'll reference those secrets in the workflow file. Now create the workflow file in `.github/workflows/git2jamf.yml`. You can use this example as a basis(replace the secret values for the names of the ones you created):

```yaml
name: git2jamf
on:
  push:
    branches: 
      - master
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: git2jamf
    steps:
      - name: checkout
        uses: actions/checkout@v2
      - name: git2jamf
        uses: jgarcesres/git2jamf@master
        with: 
          jamf_url: ${{ secrets.jamf_test_url }}
          jamf_username: ${{ secrets.jamf_test_username }}
          jamf_password: ${{ secrets.jamf_test_password }}
          script_dir: '**/scripts'
```


## Example usage with 2 instances
you would probably have 2 sets of secrets, with url and credentials for each instance(or share the same user creds across both servers). You also will need 2 workflow files: one for pushes to the master branch and another that goes to test. 

```yaml
name: git2jamf_test
on:
  pull_request:
    branches:
      - master
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
        uses: actions/checkout@v2
      - name: git2jamf_test 
        uses: jgarcesres/git2jamf@master
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
      - master
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: git2jamf
    steps:
      - name: checkout
        uses: actions/checkout@v2
      - name: git2jamf
        uses: jgarcesres/git2jamf@master
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
  pull_request:
    branches:
      - master
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: git2jamf_test
    steps:
      - name: checkout
        uses: actions/checkout@v2
      - name: git2jamf_test
        uses: jgarcesres/git2jamf@master
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
      - master
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: git2jamf
    steps:
      - name: checkout
        uses: actions/checkout@v2
      - name: git2jamf
        uses: jgarcesres/git2jamf@master
        with: 
          jamf_url: ${{ secrets.jamf_url }}
          jamf_username: ${{ secrets.jamf_username }}
          jamf_password: ${{ secrets.jamf_password }}
          script_dir: toplevelfolder/scripts
```


