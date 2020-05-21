#!/usr/bin/env python3
#created by Juan Garces

import os
import glob
import requests
import jmespath
import hashlib
import sys
from loguru import logger

logger.remove()
logger.add(sys.stdout, colorize=True, level="INFO", format="<blue>{time:HH:mm:ss!UTC}</blue>: <lvl>{message}</lvl>")


#function to get the token given the url, usrername and password
@logger.catch
def get_jamf_token(url, username, password):
    token_request = requests.post(url=f"{url}/uapi/auth/tokens", auth = (username, password))
    if token_request.status_code == requests.codes.ok:
        logger.success(f"got the token! it expires in: {token_request.json()['expires']}")
        return token_request.json()['token']
    elif token_request.status_code == requests.codes.not_found:
        logger.error('failed to retrieve a valid token, please check the url')
        raise Exception("failed to retrieve a valid token, please check the credentials")   
    elif token_request.status_code == requests.codes.unauthorized:
        logger.error('failed to retrieve a valid token, please check the credentials')
        raise Exception("failed to retrieve a valid token, please check the credentials")      
    else:
        logger.error('failed to retrieve a valid token')
        logger.error(token_request.text)
        raise Exception("failed to retrieve a valid token, please check the credentials")

#function to invalidate a token so it can't be use after we're done
@logger.catch
def invalidate_jamf_token(url, token):
    header = { "Authorization": f"Bearer {token}" }
    token_request = requests.post(url=f"{url}/uapi/auth/invalidateToken", headers=header)
    if token_request.status_code == requests.codes.no_content:
        logger.success("token invalidated succesfully")
        return True
    else:
        logger.warning("failed to invalidate the token, maybe it's already expired?")
        logger.warning(token_request.text)

#function to create a new script
@logger.catch
def create_jamf_script(url, token, payload):
    header = { f"Authorization": "Bearer {token}" }
    script_request = requests.post(url="{url}/uapi/v1/scripts", headers=header, json=payload)
    if script_request.status_code == requests.codes.created:
        logger.success("script created")
        return True
    else:
        logger.warning("failed to create the script")
        logger.debug(f"status code for put: {script_request.status_code}")
        logger.warning(script_request.text)
        sys.exit(1)


#function to update an already existing script
@logger.catch
def update_jamf_script(url, token, payload):
    header = { "Authorization": f"Bearer {token}" }
    script_request = requests.put(url=f"{url}/uapi/v1/scripts/{payload['id']}", headers=header, json=payload)
    if script_request.status_code in [requests.codes.accepted, requests.codes.ok]:
        logger.success("script was updated succesfully")
        return True
    else:
        logger.warning("failed to update the script")
        logger.debug(f"status code for put: {script_request.status_code}")
        logger.warning(script_request.text)
        sys.exit(1)

@logger.catch
def delete_jamf_script(url, token, id):
    header = { "Authorization": f"Bearer {token}" }
    script_request = requests.delete(url=f"{url}/uapi/v1/scripts/{id}", headers=header)
    if script_request.status_code in range (requests.codes.ok, requests.codes.accepted):
        logger.success("script was deleted succesfully")
        return True
    else:
        logger.warning("failed to delete the script")
        logger.debug(f"status code for delete: {script_request.status_code}")
        logger.warning(script_request.text)
        sys.exit(1)


#retrieves all scripts in a json
@logger.catch
def get_all_jamf_scripts(url, token, scripts = [], page = 0):
    header = { "Authorization": f"Bearer {token}" }
    page_size=50
    params = {"page": page, "page-size": page_size, "sort": "name:asc"}
    script_list = requests.get(url=f"{url}/uapi/v1/scripts", headers=header, params=params)
    if script_list.status_code == requests.codes.ok:
        script_list = script_list.json()
        logger.info(f"we got {len(script_list['results'])+page} of {script_list['totalCount']} results")
        page+=1
        if (page*page_size) < script_list['totalCount']:
            logger.info("seems there's more to grab")
            scripts.extend(script_list['results'])
            return get_all_jamf_scripts(url, token, scripts, page)
        else:
            logger.info("reached the end of our search")
            scripts.extend(script_list['results'])
            logger.success(f"retrieved {len(scripts)} total scripts")
            return scripts
    else:
        logger.error(f"status code: {script_list.status_code}")
        logger.error("error retrevieving script list")
        logger.error(script_list.text)
        raise Exception("error retrevieving script list")


#search for the script name and return the json that for it
@logger.catch
def find_jamf_script(url, token, script_name, page = 0):
    header = { f"Authorization": "Bearer {token}" }
    page_size=50
    params = {"page": page, "page-size": page_size, "sort": "name:asc"}
    script_list = requests.get(url=f"{url}/uapi/v1/scripts", headers=header, params=params)
    if script_list.status_code == requests.codes.ok:
        script_list = script_list.json()
        logger.info(f"we have searched {len(script_list['results'])+page} of {script_list['totalCount']} results")
        script_search = jmespath.search(f"results[?name == '{script_name}']", script_list)
        if len(script_search) == 1 :
            logger.info('found the script, returning it')
            return script_search[0]
        elif len(script_search) == 0 and (page*page_size) < script_list['totalCount']:
            logger.info("couldn't find the script in this page, seems there's more to look through")
            return find_jamf_script(url, token, script_name, page+1)
        else:
            logger.info(f"did not find any script named {script_name}")
            return "n/a"
    else:
        logger.error(f"status code: {script_list.status_code}")
        logger.error("error retrevieving script list")
        logger.error(script_list.text)
        raise Exception("failed to find the script, please investigate!")

#function to find a EA script using the filename as the script name
@logger.catch
def find_ea_script(ea_name):
    ea_script = requests.get(url=f"{url}/JSSResource/computerextensionattributes/name/{ea_name}", auth=(username,password))
    if ea_script.status_code == requests.codes.ok:
        return ea_script.json()['computer_extension_attribute']
    elif ea_script.status_code == requests.codes.not_found:
        logger.warning(f"Found no script with name: {ea_name}")
        return None
    else:
        logger.error("encountered an error retriving the extension attribute, stopping")
        logger.error(ea_script.text)
        raise Exception("encountered an error retriving the extension attribute, stopping")
        
#function to create EA script
@logger.catch
def create_ea_script(payload, id):
    headers = {"Accept": "text/xml", "Content-Type": "text/xml"}
    ea_script = requests.post(url=f"{url}/JSSResource/computerextensionattributes/id/{id}", json=payload, auth=(username,password))
    if ea_script.status_code == requests.codes.ok:
        return "success"
    else:
        logger.error("encountered an error creating the extension attribute, stopping")
        logger.error(ea_script.text)
        raise Exception("encountered an error creating the extension attribute, stopping")

#function to update existin EA script
@logger.catch
def update_ea_script(payload, id):
    headers = {"Accept": "text/xml", "Content-Type": "text/xml"}
    ea_script = requests.put(url=f"{url}/JSSResource/computerextensionattributes/id/{id}", json=payload, auth=(username,password))
    if ea_script.status_code == requests.codes.ok:
        return "success"
    else:
        logger.error("encountered an error creating the extension attribute, stopping")
        logger.error(ea_script.text)
        raise Exception("encountered an error creating the extension attribute, stopping")

#function to compare sripts and see if they have changed. If they haven't, no need to update it
@logger.catch
def compare_scripts(new, old):
    md5_new = hashlib.md5(new.encode())
    logger.info(f"hash of the of github script: {md5_new.hexdigest()}") 
    md5_old = hashlib.md5(old.encode())
    logger.info(f"hash of the of jamf script: {md5_old.hexdigest()}") 
    if md5_new.hexdigest() == md5_old.hexdigest():
        logger.info("scripts are the same")
        return True
    else:
        logger.warning("scripts are different")
        return False

#retrieves list of files given a folder path and the list of valid file extensions to look for
@logger.catch
def find_local_scripts(script_dir, script_extensions):
    script_list = []
    logger.info(f"searching for files ending in {script_extensions} in {script_dir}")
    for file_type in script_extensions:
        script_list.extend(glob.glob(f"{script_dir}/**/*.{file_type}", recursive = True))
    logger.info("found these: ", script_dir)
    logger.info(script_list)
    return script_list

#strips out the path and extension to get the scripts name
@logger.catch
def get_script_name(script_path):
    return script_path.split('/')[-1].rsplit('.', 1)[0]

@logger.catch
def push_scripts():
    #grab the token from jamf
    logger.info('grabing the token from jamf')
    token = get_jamf_token(url, username, password)
    logger.info('checking the list of local scripts to upload or create')
    scripts = {}
    #this retrives the full path of the scripts we're trying to sync from github
    scripts['github'] = find_local_scripts(script_dir, script_extensions)
    #I need to simplify this array down to the just the name of the script, stripping out the path.
    scripts['github_simple_name'] = []
    for script in scripts['github']:
        scripts['github_simple_name'].append(get_script_name(script).lower())

    logger.info('doublechecking for duplicate names')
    dupes = False
    for count, script in enumerate(scripts['github_simple_name']):
        if scripts['github_simple_name'].count(script) >= 2:
            dupes = True
            logger.error("conflicting script name")
            logger.error(scripts['github'][count])	            
    if dupes == True:
        sys.exit(1)
    #continue if no dupes are found
    logger.success("found no duplicate script names, we can continue")
    logger.info('now checking against jamf for the list of scripts')
    scripts['jamf'] =  get_all_jamf_scripts(url, token)
    logger.info("setting all script names to lower case to avoid false positives in our search.")
    logger.info("worry not, this won't affect the actual naming :)")
    #save the scripts name all in lower_case
    for script in scripts['jamf']:
        script['lower_case_name'] = script['name'].lower() 
    #make a copy of the jamf scripts, we'll use this to determine which to delete later on
    scripts['to_delete'] = scripts['jamf']
    logger.info("processing each script now")
    for count, script in enumerate(scripts['github']):
        logger.info("----------------------")
        logger.info(f"script {count+1} of {len(scripts['github'])}")
        logger.info(f"path of the script: {script}")
        script_name = get_script_name(script)
        if enable_prefix == "false":
            #don't use the prefix
            logger.info(f"script name is: {script_name}")
        else:
            #use the branch name as prefix
            prefix = branch.split('/')[-1]
            script_name = f"{prefix}_{script_name}"
            logger.info(f"the new script name: {script_name}")
        #check to see if the script name exists in jamf
        logger.info(f"now let's see if {script_name} exists in jamf already")
        script_search = jmespath.search(f"[?lower_case_name == '{script_name.lower()}']", scripts['jamf'])
        if len(script_search) == 0:
            logger.info("it doesn't exist, lets create it")
            #it doesn't exist, we can create it
            with open(script, 'r') as upload_script:
                payload = {"name": script_name, "info": "", "notes": "created via github action", "priority": "AFTER" , "categoryId": "1", "categoryName":"", "parameter4":"", "parameter5":"", "parameter6":"", "parameter7":"", "parameter8":"", "parameter9":"",  "parameter10":"", "parameter11":"", "osRequirements":"", f"scriptContents":f"{upload_script.read()}"} 
                create_jamf_script(url, token, payload)
        elif len(script_search) == 1:
            jamf_script = script_search.pop()
            del jamf_script['lower_case_name']
            scripts['to_delete'].remove(jamf_script)
            logger.info("it does exist, lets compare them")
            #it does exists, lets see if has changed
            with open(script, 'r') as upload_script:
                script_text = upload_script.read()
                if not compare_scripts(script_text, jamf_script['scriptContents']):
                    logger.info("the local version is different than the one in jamf, updating jamf")
                    #the hash of the scripts is not the same, so we'll update it
                    jamf_script['scriptContents'] = script_text
                    update_jamf_script(url, token, jamf_script)
                else:
                    logger.info("we're skipping this one.")
    if delete == 'true':
        logger.info(f"we have {len(scripts['to_delete'])} scripts left to delete")
        for script in scripts['to_delete']:
            logger.info(f"attempting to delete script {script['name']} in jamf")
            delete_jamf_script(url, token, script['id'])
      
    logger.info("expiring the token so it can't be used further")
    invalidate_jamf_token(url, token)
    logger.success("finished with the scripts, are there any EA scripts?!")  


def push_ea_scripts():
    return ""

#run this thing
if __name__ == "__main__":
    logger.info('reading environment variables')
    url = os.getenv('INPUT_JAMF_URL')
    username = os.getenv('INPUT_JAMF_USERNAME')
    password = os.getenv('INPUT_JAMF_PASSWORD')
    script_dir = os.getenv('INPUT_SCRIPT_DIR')
    ea_script_dir = os.getenv('INPUT_EA_SCRIPT_DIR')
    workspace_dir = os.getenv('GITHUB_WORKSPACE')
    if script_dir != workspace_dir:
        script_dir = f"{workspace_dir}/{script_dir}"
    enable_prefix = os.getenv('INPUT_PREFIX')
    branch = os.getenv('GITHUB_REF')
    script_extensions = os.getenv('INPUT_SCRIPT_EXTENSIONS')
    delete = os.getenv('INPUT_DELETE')
    script_extensions = script_extensions.split()
    logger.info(f"url is: {url}")
    logger.info(f"workspace dir is: {workspace_dir}")
    logger.info(f"script_dir is:  {script_dir}")
    logger.info(f"branch is: {branch}")
    logger.info(f"script_deltion is: {delete}")
    logger.info(f"scripts_extensions are: {script_extensions}")
    if enable_prefix == 'false':
        logger.warning('prefix is disabled')
    else:
        logger.warning('prefix is enabled')
    #run the block to push the "normal" scripts to jamf
    push_scripts() 
    #check to see if we have an EA scripts to push over
    if ea_script_dir != 'false':
        logger.info("we have some EA scripts to process")
        push_ea_scripts()
    else:
        logger.warning("no EA script folder set, skipping")

    logger.success("we're done!")

