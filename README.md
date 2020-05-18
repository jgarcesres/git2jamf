# git2jamf [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
This action grabs the github work directory (or any subdfolder of your choice) scans it for scripts and will compare with the scripts in jamf. It starts by comparing filename against the name of the script in jamf:
* If it doesn't exist, it will create it
* if it exists, it will compare the hash of the body of both scripts and update it in jamf if they differ. Github is always treated as the source.
* If enabled, it will add a suffix with the `branch name_`  to a script. 
## Inputs

### `jamf_url`

**Required** the url of your jamf instance

### `jamf_username`

**Required** the username to auth against jamf. *this user should have permission to update and create scripts.*

### `jamf_password`

**Required** password for the user

### `script_dir`

**optional** the directory where the scripts to upload will be, this would be a subdirectoy in your repository. By default it will try to sync all .sh and .py files from the repo. So it's **greatly recommended to provide this input**, this is a regex field so you can potentially look for multiple subdirectories, just provide a name like `**/Scripts` or `**/scripts`

### `script_extensions`

**optional** the extensions for the types of files we'll be searching for. By default it tries to look for *.sh* and *.py* files. To change the behavior, separate each input with spaces and no periods. ie `sh py ps1`

### `prefix`

**optional** by default this will be `false`, it will add the branch name as a prefix to the script before uploading it. 

## Outputs

### `results`

what scripts were updated

## Example usage with 2 instances
you would probably have 2 sets of secrets, with url and credentials for each instance(or share the same user creds across both servers, up to you). You also will need 2 workflow files: one for pushes to the master branch and another that goes to test. In this example, we disable prefix since we have 2 instances in jamf. We can keep the name of the scripts consistent between the two.

```yaml
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
    name: A job to push script changes to jamf
    steps:
      - name: checkout
        uses: actions/checkout@v2
      - name: jamf_scripts 
        uses: jgarcesres/git2jamf@master
        with: 
          jamf_url: ${{ secrets.jamf_test_url }}
          jamf_username: ${{ secrets.jamf_test_username }}
          jamf_password: ${{ secrets.jamf_test_password }}
          script_dir: '**/scripts'
```

```yaml
on:
  push:
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
        uses: jgarcesres/git2jamf@master
        with: 
          jamf_url: ${{ secrets.jamf_prod_url }}
          jamf_username: ${{ secrets.jamf_prod_username }}
          jamf_password: ${{ secrets.jamf_prod_password }}
          script_dir: '**/Scripts'
```


## Example usage with one instance
The prefix remains enabled for the test branch. This might create a bit of "garbage" as the scripts that have a prefix won't be deleted automatically. If there's any interest in this route, I can maybe make something that deletes scripts that have a certain prefix when the merge to master happens.

```yaml
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
    name: A job to push script changes to jamf
    steps:
      - name: checkout
        uses: actions/checkout@v2
      - name: jamf_scripts 
        uses: jgarcesres/git2jamf@master
        with: 
          jamf_url: ${{ secrets.jamf_url }}
          jamf_username: ${{ secrets.jamf_username }}
          jamf_password: ${{ secrets.jamf_password }}
          script_dir: scripts
          enable_prefix: true
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
        uses: jgarcesres/git2jamf@master
        with: 
          jamf_url: ${{ secrets.jamf_url }}
          jamf_username: ${{ secrets.jamf_username }}
          jamf_password: ${{ secrets.jamf_password }}
          script_dir: '**/scripts'
```


