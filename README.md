# jamf_scripts_githubaction
This action grabs the github work directory (or any of your choice) scans it for scripts and compares them against any on jamf:
* If it doesn't exist, it will create it
* if it exists, it will update it if it's different than the one in jamf.
It will add a suffix with the `branch_name_`  to any script that's not part of the master branch
## Inputs

### `jamf_url`

**Required** the url of your jamf instance

### `jamf_username`

**Required** the username to auth against jamf. *this user should have permission to update and create scripts.*

### `jamf_password`

**Required** password for the user

### `script_dir`

**optional** the directory where the scripts to upload will be. Defaults to the github.workdir environment variable

### `script_extensions`

**optional** the extensions for the types of files we'll be searching for. Defaults to *.sh* and *.py* files

### `branch_name`

**optional** branch that triggers the action. We'll use this to tag the scripts so multiple branches don't overwrite the same script


## Outputs

### `results`

what scripts were updated

## Example usage

```yaml
on:
  pull_request:
    branches: [master]
    types: [synchronize, closed]
    paths:
      - 'scripts/'
jobs:
  jamf_scripts:
    runs-on: ubuntu-latest
      name: A job to push script changes to jamf
      steps:
        - name: checkout
          uses: actions/checkout@2
        - name: jamf_scripts 
          uses: jgarcesres/jamf_scripts_action@master
          with:
            - jamf_url: ${{ secrets.jamf_url }}
            - jamf_username: ${{ secrets.jamf_username }}
            - jamf_password: ${{ secrets.jamf_password }}
        - name: grab the result
          run: echo "The result was ${{ steps.jamf_scripts.outputs.result }}"
```  