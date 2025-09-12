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


#function to get the token
@logger.catch
def get_jamf_token(url, auth_type, username, password):
    if auth_type == "auth":
        token_request = requests.post(url=f"{url}/api/v1/auth/token", auth=(username,password))
    elif auth_type =='oauth':
        data = {"client_id": username,"client_secret": password, "grant_type": "client_credentials"}
        token_request = requests.post(url=f"{url}/api/oauth/token", data=data)
    if token_request.status_code == requests.codes.ok:
        if auth_type == "auth":
            logger.success(f"got the token! it expires in: {token_request.json()['expires']}")
            return token_request.json()['token']
        elif auth_type == "oauth":
            logger.success(f"got the token! it expires in: {token_request.json()['expires_in']}")
            return token_request.json()['access_token']
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
    header = {"Authorization": f"Bearer {token}"}
    token_request = requests.post(url=f"{url}/api/v1/auth/invalidate-token", headers=header)
    if token_request.status_code == requests.codes.no_content:
        logger.success("token invalidated succesfully")
        return True
    else:
        logger.warning("failed to invalidate the token, maybe it's already expired?")
        logger.warning(token_request.text)


#function to create a new script
@logger.catch
def create_jamf_script(url, token, payload):
    header = {"Authorization": f"Bearer {token}"}
    script_request = requests.post(url=f"{url}/uapi/v1/scripts", headers=header, json=payload)
    if script_request.status_code == requests.codes.created:
        logger.success("script created")
        return True
    else:
        logger.warning("failed to create the script")
        logger.debug(f"status code for create: {script_request.status_code}")
        logger.warning(script_request.text)
        sys.exit(1)


#function to update an already existing script
@logger.catch
def update_jamf_script(url, token, payload):
    header = {"Authorization": f"Bearer {token}"}
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
    header = {"Authorization": f"Bearer {token}"}
    script_request = requests.delete(url=f"{url}/uapi/v1/scripts/{id}", headers=header)
    if script_request.status_code in  [requests.codes.ok, requests.codes.accepted, requests.codes.no_content]:
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
    header = {"Authorization": f"Bearer {token}"}
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
    header = {"Authorization": f"Bearer {token}"}
    page_size=50
    params = {"page": page, "page-size": page_size, "sort": "name:asc"}
    script_list = requests.get(url=f"{url}/uapi/v1/scripts", headers=header, params=params)
    if script_list.status_code == requests.codes.ok:
        script_list = script_list.json()
        logger.info(f"we have searched {len(script_list['results'])+page} of {script_list['totalCount']} results")
        script_search = jmespath.search(f"results[?name == '{script_name}']", script_list)
        if len(script_search) == 1:
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


#function to get all extension attributes using the new API
@logger.catch
def get_all_jamf_extension_attributes(url, token, eas = [], page = 0):
    header = {"Authorization": f"Bearer {token}"}
    page_size=50
    params = {"page": page, "page-size": page_size, "sort": "name:asc"}
    # Note: This endpoint may need verification against your Jamf Pro version
    # Common possibilities: computer-extension-attributes, computerextensionattributes, extension-attributes
    ea_list = requests.get(url=f"{url}/uapi/v1/computer-extension-attributes", headers=header, params=params)
    if ea_list.status_code == requests.codes.ok:
        ea_list = ea_list.json()
        logger.info(f"we got {len(ea_list['results'])+page} of {ea_list['totalCount']} EA results")
        page+=1
        if (page*page_size) < ea_list['totalCount']:
            logger.info("seems there's more EAs to grab")
            eas.extend(ea_list['results'])
            return get_all_jamf_extension_attributes(url, token, eas, page)
        else:
            logger.info("reached the end of our EA search")
            eas.extend(ea_list['results'])
            logger.success(f"retrieved {len(eas)} total extension attributes")
            return eas
    elif ea_list.status_code == requests.codes.not_found:
        logger.error("Extension attributes endpoint not found. This may indicate:")
        logger.error("1. The API endpoint '/uapi/v1/computer-extension-attributes' doesn't exist in your Jamf Pro version")
        logger.error("2. Your Jamf Pro version may not support extension attributes in the new API yet")
        logger.error("3. The endpoint name might be different (try checking Jamf Pro API documentation)")
        logger.error("Please verify the correct endpoint for your Jamf Pro version")
        raise Exception("Extension attributes API endpoint not found")
    else:
        logger.error(f"status code: {ea_list.status_code}")
        logger.error("error retrieving extension attribute list")
        logger.error(f"endpoint used: {url}/uapi/v1/computer-extension-attributes")
        logger.error(ea_list.text)
        raise Exception("error retrieving extension attribute list")


#function to find a specific extension attribute by name using the new API
@logger.catch
def find_jamf_extension_attribute(url, token, ea_name, page = 0):
    header = {"Authorization": f"Bearer {token}"}
    page_size=50
    params = {"page": page, "page-size": page_size, "sort": "name:asc"}
    ea_list = requests.get(url=f"{url}/uapi/v1/computer-extension-attributes", headers=header, params=params)
    if ea_list.status_code == requests.codes.ok:
        ea_list = ea_list.json()
        logger.info(f"we have searched {len(ea_list['results'])+page} of {ea_list['totalCount']} EA results")
        ea_search = jmespath.search(f"results[?name == '{ea_name}']", ea_list)
        if len(ea_search) == 1:
            logger.info('found the extension attribute, returning it')
            return ea_search[0]
        elif len(ea_search) == 0 and (page*page_size) < ea_list['totalCount']:
            logger.info("couldn't find the EA in this page, seems there's more to look through")
            return find_jamf_extension_attribute(url, token, ea_name, page+1)
        else:
            logger.info(f"did not find any extension attribute named {ea_name}")
            return "n/a"
    else:
        logger.error(f"status code: {ea_list.status_code}")
        logger.error("error retrieving extension attribute list")
        logger.error(ea_list.text)
        raise Exception("failed to find the extension attribute, please investigate!")


#function to create a new extension attribute using the new API
@logger.catch
def create_jamf_extension_attribute(url, token, payload):
    header = {"Authorization": f"Bearer {token}"}
    ea_request = requests.post(url=f"{url}/uapi/v1/computer-extension-attributes", headers=header, json=payload)
    if ea_request.status_code == requests.codes.created:
        logger.success("extension attribute created")
        return True
    elif ea_request.status_code == requests.codes.not_found:
        logger.error("Extension attributes create endpoint not found")
        logger.error("This may indicate the API endpoint doesn't exist in your Jamf Pro version")
        logger.error(f"endpoint used: {url}/uapi/v1/computer-extension-attributes")
        return False
    else:
        logger.warning("failed to create the extension attribute")
        logger.debug(f"status code for create: {ea_request.status_code}")
        logger.debug(f"endpoint used: {url}/uapi/v1/computer-extension-attributes")
        logger.warning("Response body:")
        logger.warning(ea_request.text)
        return False


#function to update an existing extension attribute using the new API
@logger.catch
def update_jamf_extension_attribute(url, token, payload):
    header = {"Authorization": f"Bearer {token}"}
    ea_request = requests.put(url=f"{url}/uapi/v1/computer-extension-attributes/{payload['id']}", headers=header, json=payload)
    if ea_request.status_code in [requests.codes.accepted, requests.codes.ok]:
        logger.success("extension attribute was updated successfully")
        return True
    elif ea_request.status_code == requests.codes.not_found:
        logger.error(f"Extension attribute with id {payload['id']} not found for update")
        logger.error(f"endpoint used: {url}/uapi/v1/computer-extension-attributes/{payload['id']}")
        return False
    else:
        logger.warning("failed to update the extension attribute")
        logger.debug(f"status code for put: {ea_request.status_code}")
        logger.debug(f"endpoint used: {url}/uapi/v1/computer-extension-attributes/{payload['id']}")
        logger.warning("Response body:")
        logger.warning(ea_request.text)
        return False


#function to delete an extension attribute using the new API
@logger.catch
def delete_jamf_extension_attribute(url, token, id):
    header = {"Authorization": f"Bearer {token}"}
    ea_request = requests.delete(url=f"{url}/uapi/v1/computer-extension-attributes/{id}", headers=header)
    if ea_request.status_code in [requests.codes.ok, requests.codes.accepted, requests.codes.no_content]:
        logger.success("extension attribute was deleted successfully")
        return True
    else:
        logger.warning("failed to delete the extension attribute")
        logger.debug(f"status code for delete: {ea_request.status_code}")
        logger.warning(ea_request.text)
        return False


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
def find_local_scripts(script_dir, script_extensions, exclude_dir=None):
    script_list = []
    logger.info(f"searching for files ending in {script_extensions} in {script_dir}")
    for file_type in script_extensions:
        script_list.extend(glob.glob(f"{script_dir}/**/*.{file_type}", recursive = True))
    
    # Filter out files from the exclude directory if specified
    if exclude_dir and exclude_dir != 'false':
        original_count = len(script_list)
        script_list = [script for script in script_list if not script.startswith(exclude_dir)]
        excluded_count = original_count - len(script_list)
        if excluded_count > 0:
            logger.info(f"excluded {excluded_count} files from EA script directory: {exclude_dir}")
    
    logger.info("found these: ", script_dir)
    logger.info(script_list)
    return script_list


#strips out the path and extension to get the scripts name
@logger.catch
def get_script_name(script_path):
    return script_path.split('/')[-1].rsplit('.', 1)[0]


@logger.catch
def push_scripts(exclude_ea_dir=None):
    #grab the token from jamf
    logger.info('grabing the token from jamf')
    token = get_jamf_token(url,auth_type, username, password)
    logger.info('checking the list of local scripts to upload or create')
    scripts = {}
    #this retrives the full path of the scripts we're trying to sync from github
    scripts['github'] = find_local_scripts(script_dir, script_extensions, exclude_ea_dir)
    #I need to simplify this array down to the just the name of the script, stripping out the path.
    scripts['github_simple_name'] = []
    for script in scripts['github']:
        scripts['github_simple_name'].append(get_script_name(script).lower())
    logger.info('doublechecking for duplicate script names')
    for count, script in enumerate(scripts['github_simple_name']):
        if scripts['github_simple_name'].count(script) >= 2:
            logger.error(f"the script name {script} is duplicated {scripts['github_simple_name'].count(script)} times, please give it a unique name")
            #logger.error(scripts['github'][count])
            sys.exit(1)
    #continue if no dupes are found
    logger.success("nice, no duplicate script names, we can continue")
    logger.info('now checking jamf for its list of scripts')
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
                payload = {"name": script_name, "info": "", "notes": "created via github action", "priority": "AFTER" , "categoryId": "1", "categoryName":"", "parameter4":"", "parameter5":"", "parameter6":"", "parameter7":"", "parameter8":"", "parameter9":"",  "parameter10":"", "parameter11":"", "osRequirements":"", "scriptContents":f"{upload_script.read()}"} 
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
        logger.warning(f"we have {len(scripts['to_delete'])} scripts left to delete")
        for script in scripts['to_delete']:
            logger.info(f"attempting to delete script {script['name']} in jamf")
            delete_jamf_script(url, token, script['id'])
      
    logger.info("expiring the token so it can't be used further")
    invalidate_jamf_token(url, token)
    logger.success("finished with the scripts")  


@logger.catch
def push_ea_scripts():
    if ea_script_dir == 'false':
        logger.warning("EA script directory not set, skipping EA script processing")
        return
    
    logger.info('starting EA script processing')
    #grab the token from jamf
    logger.info('grabbing the token from jamf for EA scripts')
    token = get_jamf_token(url, auth_type, username, password)
    logger.info('checking the list of local EA scripts to upload or create')
    ea_scripts = {}
    
    #this retrieves the full path of the EA scripts we're trying to sync from github
    ea_scripts['github'] = find_local_scripts(ea_script_dir, script_extensions)
    
    #I need to simplify this array down to just the name of the script, stripping out the path.
    ea_scripts['github_simple_name'] = []
    for ea_script in ea_scripts['github']:
        ea_scripts['github_simple_name'].append(get_script_name(ea_script).lower())
    
    logger.info('double-checking for duplicate EA script names')
    for count, ea_script in enumerate(ea_scripts['github_simple_name']):
        if ea_scripts['github_simple_name'].count(ea_script) >= 2:
            logger.error(f"the EA script name {ea_script} is duplicated {ea_scripts['github_simple_name'].count(ea_script)} times, please give it a unique name")
            sys.exit(1)
    
    #continue if no dupes are found
    logger.success("nice, no duplicate EA script names, we can continue")
    logger.info('now checking jamf for its list of extension attributes')
    ea_scripts['jamf'] = get_all_jamf_extension_attributes(url, token)
    logger.info("setting all EA names to lower case to avoid false positives in our search.")
    logger.info("worry not, this won't affect the actual naming :)")
    
    #save the EA names all in lower_case
    for ea_script in ea_scripts['jamf']:
        ea_script['lower_case_name'] = ea_script['name'].lower()
    
    #make a copy of the jamf EAs, we'll use this to determine which to delete later on
    ea_scripts['to_delete'] = ea_scripts['jamf']
    
    logger.info("processing each EA script now")
    for count, ea_script in enumerate(ea_scripts['github']):
        logger.info("----------------------")
        logger.info(f"EA script {count+1} of {len(ea_scripts['github'])}")
        logger.info(f"path of the EA script: {ea_script}")
        ea_script_name = get_script_name(ea_script)
        
        if enable_prefix == "false":
            #don't use the prefix
            logger.info(f"EA script name is: {ea_script_name}")
        else:
            #use the branch name as prefix
            prefix = branch.split('/')[-1]
            ea_script_name = f"{prefix}_{ea_script_name}"
            logger.info(f"the new EA script name: {ea_script_name}")
        
        #check to see if the EA script name exists in jamf
        logger.info(f"now let's see if {ea_script_name} exists in jamf already")
        ea_search = jmespath.search(f"[?lower_case_name == '{ea_script_name.lower()}']", ea_scripts['jamf'])
        
        if len(ea_search) == 0:
            logger.info("it doesn't exist, lets create it")
            #it doesn't exist, we can create it
            with open(ea_script, 'r') as upload_ea_script:
                ea_script_content = upload_ea_script.read()
                payload = {
                    "name": ea_script_name,
                    "enabled": True,
                    "description": "Extension attribute script created via git2jamf",
                    "dataType": "String",
                    "inputType": {
                        "type": "Script",
                        "platform": "Mac",
                        "script": ea_script_content
                    },
                    "inventoryDisplay": "General",
                    "reconDisplay": "Extension Attributes"
                }
                create_jamf_extension_attribute(url, token, payload)
                
        elif len(ea_search) == 1:
            jamf_ea = ea_search.pop()
            del jamf_ea['lower_case_name']
            ea_scripts['to_delete'].remove(jamf_ea)
            logger.info("it does exist, lets compare them")
            #it does exist, lets see if it has changed
            with open(ea_script, 'r') as upload_ea_script:
                ea_script_content = upload_ea_script.read()
                # Check if the script content is different
                current_script = ""
                if 'inputType' in jamf_ea and 'script' in jamf_ea['inputType']:
                    current_script = jamf_ea['inputType']['script']
                
                if not compare_scripts(ea_script_content, current_script):
                    logger.info("the local EA version is different than the one in jamf, updating jamf")
                    #the hash of the scripts is not the same, so we'll update it
                    jamf_ea['inputType']['script'] = ea_script_content
                    update_jamf_extension_attribute(url, token, jamf_ea)
                else:
                    logger.info("we're skipping this EA script.")
    
    if delete == 'true':
        logger.warning(f"we have {len(ea_scripts['to_delete'])} extension attributes left to delete")
        for ea_script in ea_scripts['to_delete']:
            # Only delete extension attributes that have scripts (not other types like text input, etc.)
            if 'inputType' in ea_script and ea_script['inputType'].get('type', '').lower() == 'script':
                logger.info(f"attempting to delete extension attribute {ea_script['name']} in jamf")
                delete_jamf_extension_attribute(url, token, ea_script['id'])
            else:
                logger.info(f"skipping deletion of non-script extension attribute: {ea_script['name']}")
    
    logger.info("expiring the token so it can't be used further")
    invalidate_jamf_token(url, token)
    logger.success("finished with the EA scripts")


#run this thing
if __name__ == "__main__":
    logger.info('reading environment variables')
    url = os.getenv('INPUT_JAMF_URL')
    auth_type = os.getenv("INPUT_JAMF_AUTH_TYPE")
    if auth_type not in ["auth","oauth"]:
        logger.error("please use 'auth' or 'oauth' as they auth_type")
    #if using oauth, we're just going to re-use the same variables as they are similar enough. 
    #client_id is username
    username = os.getenv('INPUT_JAMF_USERNAME')
    #client_secret is password
    password = os.getenv('INPUT_JAMF_PASSWORD')
    script_dir = os.getenv('INPUT_SCRIPT_DIR')
    ea_script_dir = os.getenv('INPUT_EA_SCRIPT_DIR')
    workspace_dir = os.getenv('GITHUB_WORKSPACE')
    if script_dir != workspace_dir:
        script_dir = f"{workspace_dir}/{script_dir}"
    # Process EA script directory path if it's set
    if ea_script_dir != 'false' and ea_script_dir != workspace_dir:
        ea_script_dir = f"{workspace_dir}/{ea_script_dir}"
    enable_prefix = os.getenv('INPUT_PREFIX')
    branch = os.getenv('GITHUB_REF')
    script_extensions = os.getenv('INPUT_SCRIPT_EXTENSIONS')
    delete = os.getenv('INPUT_DELETE')
    script_extensions = script_extensions.split()
    logger.info(f"url is: {url}")
    logger.info(f"workspace dir is: {workspace_dir}")
    logger.info(f"script_dir is:  {script_dir}")
    logger.info(f"ea_script_dir is: {ea_script_dir}")
    logger.info(f"branch is set to: {branch}")
    logger.info(f"script_deletion is: {delete}")
    logger.info(f"scripts_extensions are: {script_extensions}")
    if enable_prefix == 'false':
        logger.warning('prefix is disabled')
    else:
        logger.warning(f"prefix enabled, using: {branch.split('/')[-1]}")
    #run the block to push the "normal" scripts to jamf
    push_scripts(ea_script_dir if ea_script_dir != 'false' else None) 
    #check to see if we have an EA scripts to push over
    if ea_script_dir != 'false':
        logger.info("we have some EA scripts to process")
        push_ea_scripts()
    else:
        logger.warning("no EA script folder set, skipping")

    logger.success("we're done!")