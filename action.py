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
logger.add(sys.stderr, colorize=True, level="ERROR", format="<red>{time}</red> <level>{message}</level>")
logger.add(sys.stderr, colorize=True, level="WARNING", format="<magenta>{time}</magenta> <level>{message}</level>")
logger.add(sys.stdout, colorize=True, level="INFO", format="<blue>{time}</blue> <level>{message}</level>")


#function to get the token given the url, usrername and password
@logger.catch
def get_jamf_token(url, username, password):
    token_request = requests.post(url='{}/uapi/auth/tokens'.format(url), auth = (username, password))
    if token_request.status_code in range(200, 203):
        logger.success("got the token! it expires in: {}".format(token_request.json()['expires']))
        return token_request.json()['token']
    elif token_request.status_code == 404:
        logger.critical('failed to retrieve a valid token, please check the url')   
    elif token_request.status_code == 401:
        logger.critical('failed to retrieve a valid token, please check the credentials')      
    else:
        logger.critical('failed to retrieve a valid token')
        logger.warning(token_request.text)

#function to invalidate a token so it can't be use after we're done
@logger.catch
def invalidate_jamf_token():
    header = { "Authorization": "Bearer {}".format(token) }
    token_request = requests.post(url='{}/uapi/auth/invalidateToken'.format(url), headers=header)
    if token_request.status_code in range(200, 300):
        logger.success("token invalidated succesfully")
        return True
    else:
        logger.warning("failed to invalidate the token, maybe it's already expired?")
        logger.warning(token_request.text)

#function to update an already existing script
@logger.catch
def update_jamf_script(payload):
    header = { "Authorization": "Bearer {}".format(token) }
    script_request = requests.put(url='{}/uapi/v1/scripts/{}'.format(url, payload['id']), headers=header, json=payload)
    if script_request.status_code in range(200, 300):
        logger.success("script was updated succesfully")
        return True
    else:
        logger.warning("failed to update the script")
        logger.warning(script_request.text)

#function to create a new script
@logger.catch
def create_jamf_script(payload):
    header = { "Authorization": "Bearer {}".format(token) }
    script_request = requests.post(url='{}/uapi/v1/scripts'.format(url), headers=header, json=payload)
    if script_request.status_code in range(200, 300):
        logger.success("script created")
        return True
    else:
        logger.warning("failed to create the sript")
        logger.warning(script_request.text)


#retrieves all scripts in a json
@logger.catch
def get_jamf_scripts(scripts = [], page = 0):
    header = { "Authorization": "Bearer {}".format(token) }
    page_size=50
    params = {"page": page, "page-size": page_size, "sort": "name:asc"}
    script_list = requests.get(url='{}/uapi/v1/scripts'.format(url), headers=header, params=params)
    if script_list.status_code in range(200,205):
        script_list = script_list.json()
        logger.info("we have searched {} of {} results".format(len(script_list['results'])+page, script_list['totalCount']))
        page+=1
        if (page*page_size) < script_list['totalCount']:
            logger.info("seems there's more to grab")
            scripts.extend(script_list['results'])
            return get_jamf_scripts(scripts, page)
        else:
            logger.info("reached the end of our search")
            scripts.extend(script_list['results'])
            logger.success("retrieved {} total scripts".format(len(scripts)))
            return scripts
    else:
        logger.critical("status code: {}".format(script_list.status_code))
        logger.critical("error retrevieving script list")
        logger.critical(script_list.text)
        exit(1)


#search for the script name and return the json that represents it
@logger.catch
def find_jamf_script(script_name, page = 0):
    header = { "Authorization": "Bearer {}".format(token) }
    page_size=50
    params = {"page": page, "page-size": page_size, "sort": "name:asc"}
    script_list = requests.get(url='{}/uapi/v1/scripts'.format(url), headers=header, params=params)
    if script_list.status_code in range(200, 205):
        script_list = script_list.json()
        logger.info("we have searched {} of {} results".format(len(script_list['results'])+page, script_list['totalCount']))
        script_search = jmespath.search("results[?name == '{}']".format(script_name), script_list)
        if len(script_search) == 1 :
            logger.info('found the script, returning it')
            return script_search[0]
        elif len(script_search) == 0 and (page*page_size) < script_list['totalCount']:
            logger.info("couldn't find the script in this page, seems there's more to look through")
            return find_jamf_script(script_name, page+1)
        else:
            logger.info("did not find any script named {}".format(script_name))
            return "n/a"
    else:
        logger.critical("status code: {}".format(script_list.status_code))
        logger.critical("error retrevieving script list")
        logger.critical(script_list.text)
        exit(1)

#function to compare sripts and see if they have changed. If they haven't, no need to update it
@logger.catch
def compare_scripts(new, old):
    md5_new = hashlib.md5(new.encode()) 
    md5_old = hashlib.md5(old.encode())
    if md5_new.hexdigest() == md5_old.hexdigest():
        logger.info("scripts are the same")
        return True
    else:
        logger.info("scripts are different")
        return False

#retrieves list of files given a folder path and the list of valid file extensions to look for
@logger.catch
def find_local_scripts(script_dir, script_extensions):
    script_list = []
    logger.info('searching for files ending in {} in {}'.format(script_extensions, script_dir))
    for file_type in script_extensions:
        script_list.extend(glob.glob('{}/**/*.{}'.format(script_dir, file_type), recursive = True))
    logger.info("found these: in {}", script_dir)
    logger.info(script_list)
    return script_list

#strips out the path and extension to get the scripts name
@logger.catch
def get_script_name(script_path):
    return script_path.split('/')[-1].split('.')[0]



if __name__ == "__main__":
    logger.info('reading environment variables')
    #jamf_args = read_args(sys.argv[1:])
    url = os.environ['INPUT_JAMF_URL']
    username = os.environ['INPUT_JAMF_USERNAME']
    password = os.environ['INPUT_JAMF_PASSWORD']
    script_dir = os.environ['INPUT_SCRIPT_DIR']
    workspace_dir = os.environ['GITHUB_WORKSPACE']
    if script_dir != workspace_dir:
        script_dir = '{}/{}'.format(workspace_dir,script_dir)
    prefix = os.environ['INPUT_BRANCH_NAME']
    script_extensions = os.environ['INPUT_SCRIPT_EXTENSIONS']
    script_extensions = script_extensions.split()
    excluded_scripts = []
    logger.info('url is: ' + url)
    logger.info('workspace dir is: ' + workspace_dir)
    logger.info('script_dir is: ' + script_dir)
    logger.info('branch is: ' + prefix)
    logger.info('scripts_extensions are: {}'.format(script_extensions))

    #grab the token from jamf
    logger.info('grabing the token from jamf')
    token = get_jamf_token(url, username, password)
    logger.info('got the token, checking the list of local scripts to upload or create')
    local_scripts = find_local_scripts(script_dir, script_extensions)
    #I need to simplify this array down to the just the name of the script and compare to avoid dupes
    simple_name_local_scripts = []
    for script in local_scripts:
        simple_name_local_scripts.append(get_script_name(script).lower())
    logger.info('doublechecking for duplicate names. if we have any, they will be excluded')
    for script in simple_name_local_scripts:
        search = jmespath.search("[?name == '{}']".format(script), simple_name_local_scripts)
        if len(search) >= 2:
            logger.warning("found a conflicting script name, please resolve it. it will be excluded from this run")
            logger.warning("excluded: {}".format(script))
            excluded_scripts.append(script)
    logger.info("list of excluded scripts {}".format(excluded_scripts))
    logger.info('now checking against jamf for the list of scripts')
    jamf_scripts = get_jamf_scripts()
    logger.info("setting all script names to lower case to avoid false positives in our search. \n Worry not, this won't affect the actual naming :)")
    for script in jamf_scripts:
        script['lower_case_name'] = script['name'].lower() 
    logger.info("got the list from jamf")
    logger.info("processing each script now")
    for count, script in enumerate(local_scripts):
        logger.info("----------------------")
        logger.info("script {} of {} ".format(count+1, len(local_scripts)))
        script_name = get_script_name(script)
        if script_name.lower() in excluded_scripts:
            logger.info('this is one of the excluded scripts, skipping {}'.format(script_name))
            logger.info('full path of the script is {}'.format(script))
            continue
        elif 'master' in prefix:
            logger.info(" we're in the master branch, we won't use the prefix")
            #if this is the master branch we'll go with the vanilla name
            logger.info("script name is: {}".format(script_name))
        else:
            logger.info("not the master branch, using the branch name as a prefix")
            #if it's not the master branch then we will use the branch name as a prefix_
            prefix = prefix.split('/')[-1]
            script_name = "{}_{}".format(prefix,script_name)
            logger.info("new scripts name: {}".format(script_name))
        #check to see if the script name exists in jamf
        logger.info("now let's see if the scripts we're processing exists in jamf already")
        script_search = jmespath.search("[?lower_case_name == '{}']".format(script_name.lower()), jamf_scripts)
        if len(script_search) == 0:
            logger.info("doesn't exist, lets create it")
            #it doesn't exist, we can create it
            with open(script, 'r') as upload_script:
                payload = {"name": script_name, "info": "", "notes": "created via github action", "priority": "AFTER" , "categoryId": "1", "categoryName":"", "parameter4":"", "parameter5":"", "parameter6":"", "parameter7":"", "parameter8":"", "parameter9":"",  "parameter10":"", "parameter11":"", "osRequirements":"", "scriptContents":"{}".format(upload_script.read()) } 
                create_jamf_script(payload)
        elif len(script_search) == 1:
            jamf_script = script_search.pop()
            del jamf_script['lower_case_name']
            logger.info("it does exist, lets update it!")
            #it does exists, lets see if has changed
            with open(script, 'r') as upload_script:
                script_text = upload_script.read()
                if not compare_scripts(script_text, jamf_script['scriptContents']):
                    logger.info("the local version is different than the one in jamf, updating jamf")
                    #the hash of the scripts is not the same, so we'll update it
                    jamf_script['scriptContents'] = script_text
                    update_jamf_script(jamf_script)
                else:
                    logger.info("since the scripts are still the same, we're skipping this one.")
    
    logger.info("expiring the token so it can't be used further")
    invalidate_jamf_token()
    logger.success("finished!")

