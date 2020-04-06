#!/usr/bin/env python3
#created by Juan Garces

import os
import glob
import requests
import logging
import jmespath
import hashlib

#testing
# from dotenv import load_dotenv
# load_dotenv()


#import getopt 
# def read_args(argv):
#     jamf_args= {}
#     try:
#         opts, args = getopt.getopt(argv,"hU:u:p:",["url=","username=", "password"])
#     except getopt.GetoptError:
#         print 'action.py -U url -u <username> -p <password>'
#         sys.exit(2)
#     for opt, arg in opts:
#         if opt == '-h':
#             print 'action.py -U url -u <username> -p <password>'
#             sys.exit()
#         elif opt in ("-U", "--url"):
#             jamf_args['url'] = arg
#         elif opt in ("-u", "--username"):
#             jamf_args['username'] = arg
#         elif opt in ("-p", "--password"):
#             jamf_args['password'] = arg
#     return jamf_args


#function to get the token given the url, usrername and password
def get_jamf_token(url, username, password):
    token_request = requests.post(url='{}/uapi/auth/tokens'.format(url), auth = (username, password))
    if token_request.status_code in range(200, 203):
        print("got the token! it expires in: {}".format(token_request.json()['expires']))
        return token_request.json()['token']
    elif token_request.status_code == 404:
        print("::set-output name=result::{}".format('bad request, check your url'))
        print('failed to retrieve a valid token, please check the url')   
    elif token_request.status_code == 401:
        print("::set-output name=result::{}".format('credentials are invalid, please doublecheck them'))
        print('failed to retrieve a valid token, please check the credentials')      
    else:
        print("::set-output name=result::{}".format('failed to retrieve the token'))
        print('failed to retrieve a valid token')
        print(token_request.text)

#function to invalidate a token so it can't be use after we're done
def invalidate_jamf_token():
    header = { "Authorization": "Bearer {}".format(token) }
    token_request = requests.post(url='{}/uapi/auth/invalidateToken'.format(), headers=header)
    if token_request.status_code in range(200, 300):
        print("token invalidated succesfully")
        return True
    else:
        print("failed to invalidate the token, maybe it's already expired?")
        print(token_request.text)

#function to update an already existing script
def update_jamf_script(payload):
    header = { "Authorization": "Bearer {}".format(token) }
    script_request = requests.put(url='{}/uapi/v1/scripts/{}'.format(url, payload['id']), headers=header, json=payload)
    if script_request.status_code in range(200, 300):
        print("script succesfully")
        return True
    else:
        print("::set-output name=result::{}".format('failed to update script: {}'.format(payload['name'])))
        print("failed to update the script")
        print(script_request.content)

#function to create a new script
def create_jamf_script(payload):
    header = { "Authorization": "Bearer {}".format(token) }
    script_request = requests.post(url='{}/uapi/v1/scripts'.format(url), headers=header, json=payload)
    if script_request.status_code in range(200, 300):
        print("script created")
        return True
    else:
        print("::set-output name=result::{}".format('failed to update script: {}'.format(payload['name'])))
        print("failed to create the sript")
        print(script_request.content)


#retrieves all scripts in a json
def get_jamf_scripts(scripts = [], page = 0):
    header = { "Authorization": "Bearer {}".format(token) }
    page_size=50
    params = {"page": page, "page-size": page_size, "sort": "name:asc"}
    script_list = requests.get(url='{}/uapi/v1/scripts'.format(url), headers=header, params=params)
    if script_list.status_code in range(200, 300):
        script_list = script_list.json()
        print("we have searched {} of {} results".format(len(script_list['results'])+page, script_list['totalCount']))
        if (page*page_size) < script_list['totalCount']:
            print("seems there's more to grab")
            scripts.extend(script_list['results'])
            return get_jamf_scripts(scripts, page+1)
        else:
            print("reached the end of our search")
            scripts.extend(script_list['results'])
            return scripts
    else:
        print("::set-output name=result::{}".format('failed to retrieve scripts from jamf'))
        print("status code: {}".format(script_list.status_code))
        print("error retrevieving script list")
        print(token_request.text)
        exit(1)


#search for the script name and return the json that represents it
def find_jamf_script(script_name, page = 0):
    header = { "Authorization": "Bearer {}".format(token) }
    page_size=50
    params = {"page": page, "page-size": page_size, "sort": "name:asc"}
    script_list = requests.get(url='{}/uapi/v1/scripts'.format(url), headers=header, params=params)
    if script_list.status_code in range(200, 300):
        script_list = script_list.json()
        print("we have searched {} of {} results".format(len(script_list['results'])+page, script_list['totalCount']))
        script_search = jmespath.search("results[?name == '{}']".format(script_name), script_list)
        if len(script_search) == 1 :
            print('found the script, returning it')
            return script_search[0]
        elif len(script_search) == 0 and (page*page_size) < script_list['totalCount']:
            print("couldn't find the script in this page, seems there's more to look through")
            return find_jamf_script(script_name, page+1)
        else:
            print("did not find any script named {}".format(script_name))
            return "n/a"
    else:
        print("::set-output name=result::{}".format('failed to retrieve script from jamf'))
        print("status code: {}".format(script_list.status_code))
        print("error retrevieving script list")
        print(token_request.text)
        exit(1)

#function to compare sripts and see if they have changed. If they haven't, no need to update it
def compare_scripts(new, old):
    md5_new = hashlib.md5(new.encode()) 
    md5_old = hashlib.md5(old.encode())
    if md5_new.hexdigest() == md5_old.hexdigest():
        print("scripts are the same")
        return True
    else:
        print("scripts are different")
        return False

#retrieves list of files given a folder path and the list of valid file extensions to look for
def find_local_scripts(script_dir, script_extensions):
    script_list = []
    print('searching for files ending in {} in {}'.format(script_extensions, script_dir))
    for file_type in script_extensions:
        script_list.extend(glob.glob('{}/**/*.{}'.format(script_dir, file_type), recursive = True))
    print("found these: ")
    print(script_list)
    return script_list

#strips out the path and extension to get the scripts name
def get_script_name(script_path):
    return script_path.split('/')[-1].split('.')[0]



if __name__ == "__main__":
    print('reading environment variables')
    #jamf_args = read_args(sys.argv[1:])
    url = os.environ['INPUT_JAMF_URL']
    username = os.environ['INPUT_JAMF_USERNAME']
    password = os.environ['INPUT_JAMF_PASSWORD']
    script_dir = os.environ['INPUT_SCRIPT_DIR']
    workspace_dir = os.environ['GITHUB_WORKSPACE']
    if script_dir != workspace_dir:
        script_dir = '{}/{}'.format(workspace_dir,script_dir)
    suffix = os.environ['INPUT_BRANCH_NAME']
    script_extensions = os.environ['INPUT_SCRIPT_EXTENSIONS']
    script_extensions = script_extensions.split()
    
    print('url is: '+url)
    print('workspace dir is: '+workspace_dir)
    print('script_dir is: '+script_dir)
    print('suffix is: '+suffix)
    print('scripts_extensions are: {}'.format(script_extensions))

    #grab the token from jamf
    print('grabing the token from jamf')
    token = get_jamf_token(url, username, password)
    print('got the token, checking the list of local scripts to upload or create')
    local_scripts = find_local_scripts(script_dir, script_extensions)
    print('now checking against jamf for the list of scripts')
    jamf_scripts = get_jamf_scripts()
    
    for script in local_scripts:
        if 'master' in suffix:
            print(" we're in the master branch, we won't use the suffix")
            #if this is the master branch we'll go with the vanilla name
            script_name = get_script_name(script)
        else:
            print("not the master branch, using the branch name as a suffix")
            #if it's not the master branch then we will use the branch name as a suffix_
            script_name = "{}_{}".format(suffix.strip('/')[-1],get_script_name(script))
            print("new scripts name: {}".format(script_name))
        #check to see if the script name exists in jamf
        print("now let's see if the scripts we're processing exists in jamf already")
        script_search = jmespath.search("[?name == '{}']".format(script_name), jamf_scripts)
        if len(script_search) == 0:
            print("doesn't exist, lets create it")
            #it doesn't exist, we can create it
            with open(script, 'r') as upload_script:
                payload = {"name": script_name, "info": "", "notes": "created via github action", "priority": "AFTER" , "categoryId": "1", "categoryName":"", "parameter4":"", "parameter5":"", "parameter6":"", "parameter7":"", "parameter8":"", "parameter9":"",  "parameter10":"", "parameter11":"", "osRequirements":"", "scriptContents":"{}".format(upload_script.read()) } 
                create_jamf_script(payload)
        elif len(script_search == 1):
            print("it does exist, lets update it!")
            #it does exists, lets see if has changed
            with open(script, 'r') as upload_script:
                script_text = upload_script.read()
                if not compare_scripts(script_text, script_search[0]['scriptContents']):
                    #the hash of the scripts is not the same, so we'll update it
                    script['scriptContents'] =  "{}".format(script_text)
                    update_jamf_script(script)
    


