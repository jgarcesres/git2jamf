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

**optional** the directory where the scripts to upload will be, this would be a subdirectoy in your repository. By default it will try to sync all .sh and .py files from the repo. So it's greatly recommended to provide this input, this is a regex field so you can potentially look for multiple subdirectories, just provide a name like `**/Scripts` or `**/scripts`

### `script_extensions`

**optional** the extensions for the types of files we'll be searching for. By default it tries to look for *.sh* and *.py* files. To change the behavior, separate each input with spaces and no periods. ie `sh py ps1`

### `prefix_name`

**optional** by default will be the name of the branch that triggers the action. We'll use this to tag the scripts so multiple branches don't overwrite the same script


## Outputs

### `results`

what scripts were updated

## Example usage

```yaml
on:
  push:
    branches: 
      - master
      - dev*
      - test*
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
    name: A job to push script changes to jamf
    steps:
      - name: checkout
        uses: actions/checkout@v2
      - name: jamf_scripts 
        uses: jgarcesres/git2jamf@v1
        with: 
          jamf_url: ${{ secrets.jamf_url }}
          jamf_username: ${{ secrets.jamf_username }}
          jamf_password: ${{ secrets.jamf_password }}
          script_dir: scripts
```  
