# git2jamf
This action grabs the github work directory (or any of your choice) scans it for scripts and compares them against a pull of all scripts on jamf:
* If it doesn't exist, it will create it
* if it exists, it will compare the two and update it in jamf if they differ. Github is always treated as the source.
* It will add a suffix with the `branch name_`  to any script that's not part of the master branch
## Inputs

### `jamf_url`

**Required** the url of your jamf instance

### `jamf_username`

**Required** the username to auth against jamf. *this user should have permission to update and create scripts.*

### `jamf_password`

**Required** password for the user

### `script_dir`

**optional** the directory where the scripts to upload will be, this would be a subdirectoy in your repository. By default it will try to sync all .sh and .py files from the repo. So it's *greatly recommended to provide this input*, this is a regex field so you can potentially look for multiple subdirectories, just provide a name like `**/Scripts` or `**/scripts`

### `script_extensions`

**optional** the extensions for the types of files we'll be searching for. By default it tries to look for *.sh* and *.py* files. To change the behavior, separate each input with spaces and no periods. ie `sh py ps1`

### `enable_prefix`

**optional** by default this will be `true`, it will add the branch name as a prefix to the script before uploading it. You probably want to disable this for pushes to your `master` so it can send a clean file name to your production instance.

## Outputs

### `results`

what scripts were updated

## Example usage 

```yaml
on:
  push:
    branches: 
      - test
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: A job to push script changes to jamf
    steps:
      - name: checkout
        uses: actions/checkout@v2
      - name: jamf_scripts 
        uses: jgarcesres/git2jamf@v.1
        with: 
          jamf_url: ${{ secrets.jamf_url }}
          jamf_username: ${{ secrets.jamf_username }}
          jamf_password: ${{ secrets.jamf_password }}
          script_dir: scripts
```  

## Example usage with 2 instances
you would probably have 2 sets of secrets, with url and credentials for each instance. You also will probably need 2 files. One for pushes, commits or PR's to the master branch. And another that goes to test. In this example, we disable prefix since we have 2 instances in jamf. We can keep the name of the scripts consistent between the two.

```yaml
on:
  push:
    branches: 
      - test*
      - dev*
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: A job to push script changes to jamf
    steps:
      - name: checkout
        uses: actions/checkout@v2
      - name: jamf_scripts 
        uses: jgarcesres/git2jamf@v.1
        with: 
          jamf_url: ${{ secrets.jamf_test_url }}
          jamf_username: ${{ secrets.jamf_test_username }}
          jamf_password: ${{ secrets.jamf_test_password }}
          script_dir: '**/scripts'
          enable_prefix: false
```

```yaml
on:
  pull_request:
    branches: 
      - master
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: A job to push script changes to production in jamf
    steps:
      - name: checkout
        uses: actions/checkout@v2
      - name: jamf_scripts 
        uses: jgarcesres/git2jamf@v.1
        with: 
          jamf_url: ${{ secrets.jamf_prod_url }}
          jamf_username: ${{ secrets.jamf_prod_username }}
          jamf_password: ${{ secrets.jamf_prod_password }}
          script_dir: '**/Scripts'
          enable_prefix: false
```