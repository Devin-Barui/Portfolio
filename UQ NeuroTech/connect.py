import websocket #'pip install websocket-client' for install
from datetime import datetime
import asyncio
import json
import ssl
import time
import sys
import os
from pydispatch import Dispatcher #'pip install python-dispatch' for install
import warnings
import threading

# Server request IDs:

# define request id
QUERY_HEADSET_ID                    =   1
CONNECT_HEADSET_ID                  =   2
REQUEST_ACCESS_ID                   =   3
AUTHORIZE_ID                        =   4
CREATE_SESSION_ID                   =   5
SUB_REQUEST_ID                      =   6
SETUP_PROFILE_ID                    =   7
QUERY_PROFILE_ID                    =   8
TRAINING_ID                         =   9
DISCONNECT_HEADSET_ID               =   10
CREATE_RECORD_REQUEST_ID            =   11
STOP_RECORD_REQUEST_ID              =   12
EXPORT_RECORD_ID                    =   13
INJECT_MARKER_REQUEST_ID            =   14
SENSITIVITY_REQUEST_ID              =   15
MENTAL_COMMAND_ACTIVE_ACTION_ID     =   16
MENTAL_COMMAND_BRAIN_MAP_ID         =   17
MENTAL_COMMAND_TRAINING_THRESHOLD   =   18
SET_MENTAL_COMMAND_ACTIVE_ACTION_ID =   19
HAS_ACCESS_RIGHT_ID                 =   20
GET_CURRENT_PROFILE_ID              =   21
GET_CORTEX_INFO_ID                  =   22
UPDATE_MARKER_REQUEST_ID            =   23
UNSUB_REQUEST_ID                    =   24

#define error_code
ERR_PROFILE_ACCESS_DENIED = -32046

# define warning code
CORTEX_STOP_ALL_STREAMS = 0
CORTEX_CLOSE_SESSION = 1
USER_LOGIN = 2
USER_LOGOUT = 3
ACCESS_RIGHT_GRANTED = 9
ACCESS_RIGHT_REJECTED = 10
PROFILE_LOADED = 13
PROFILE_UNLOADED = 14
CORTEX_AUTO_UNLOAD_PROFILE = 15
EULA_ACCEPTED = 17
DISKSPACE_LOW = 19
DISKSPACE_CRITICAL = 20
HEADSET_CANNOT_CONNECT_TIMEOUT = 102
HEADSET_DISCONNECTED_TIMEOUT = 103
HEADSET_CONNECTED = 104
HEADSET_CANNOT_WORK_WITH_BTLE = 112
HEADSET_CANNOT_CONNECT_DISABLE_MOTION = 113

class Connect(Dispatcher):
    """
    Dispatcher used for Observer-Spectator design pattern setup.
    
    """
    _events_ = ['inform_error','create_session_done', 'query_profile_done', 'load_unload_profile_done', 
                'save_profile_done', 'get_mc_active_action_done','mc_brainmap_done', 'mc_action_sensitivity_done', 
                'mc_training_threshold_done', 'create_record_done', 'stop_record_done','warn_cortex_stop_all_sub', 
                'inject_marker_done', 'update_marker_done', 'export_record_done', 'new_data_labels', 
                'new_com_data', 'new_fe_data', 'new_eeg_data', 'new_mot_data', 'new_dev_data', 
                'new_met_data', 'new_pow_data', 'new_sys_data', 'stream_sub_done']
    
    def __init__(self, client_id, client_secret, debug_mode=False, **kwargs):
        
        self.session_id = ''
        self.headset_id = ''
        self.debug = debug_mode
        self.debit = 10
        self.license = ''

        if client_id == '':
            raise ValueError('Empty your_app_client_id. Please fill in your_app_client_id before running the example.')
        else:
            self.client_id = client_id

        if client_secret == '':
            raise ValueError('Empty your_app_client_secret. Please fill in your_app_client_secret before running the example.')
        else:
            self.client_secret = client_secret

        for key, value in kwargs.items():
            print('init {0} - {1}'.format(key, value))
            if key == 'license':
                self.license = value
        
    def open(self):
        url = "wss://localhost:6868"
        # websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(url, 
                                        on_message=self.on_message,
                                        on_open = self.on_open,
                                        on_error=self.on_error,
                                        on_close=self.on_close)
        threadName = "WebsockThread:-{:%Y%m%d%H%M%S}".format(datetime.utcnow())
        
        # Certificate is required by default.
        # Make sure the rootCA.pem file is in the same folder. 
        # Otherwise change the below line to the directory of the rootCA file or opt for the no certificate option.

        #sslopt = {'ca_certs': "./rootCA.pem", "cert_reqs": ssl.CERT_REQUIRED}
        sslopt={"cert_reqs": ssl.CERT_NONE}
        
        self.websock_thread  = threading.Thread(target=self.ws.run_forever, args=(None, sslopt), name=threadName)
        self.websock_thread .start()

    def close(self):
        self.ws.close()

    def set_wanted_headset(self, headsetId):
        self.headset_id = headsetId

    def set_wanted_profile(self, profileName):
        self.profile_name = profileName

    def on_open(self, *args, **kwargs):
        print("websocket opened")
        self.do_prepare_steps()

    def on_error(self, *args):
        if len(args) == 2:
            print(str(args[1]))

    def on_close(self, *args, **kwargs):
        print("on_close")
        print(args[1])

    def handle_result(self, recv_dic):
        if self.debug:
            print(recv_dic)

        req_id = recv_dic['id']
        result_dic = recv_dic['result']

        if req_id == HAS_ACCESS_RIGHT_ID:
            access_granted = result_dic['accessGranted']
            if access_granted == True:
                # authorize
                self.authorize()
            else:
                # request access
                self.request_access()
        elif req_id == REQUEST_ACCESS_ID:
            access_granted = result_dic['accessGranted']

            if access_granted == True:
                # authorize
                self.authorize()
            else:
                # wait approve from Emotiv Launcher
                msg = result_dic['message']
                warnings.warn(msg)
        elif req_id == AUTHORIZE_ID:
            print("Authorize successfully.")
            self.auth = result_dic['cortexToken']
            # query headsets
            self.query_headset()
        elif req_id == QUERY_HEADSET_ID:
            self.headset_list = result_dic
            found_headset = False
            headset_status = ''
            for ele in self.headset_list:
                hs_id = ele['id']
                status = ele['status']
                connected_by = ele['connectedBy']
                print('headsetId: {0}, status: {1}, connected_by: {2}'.format(hs_id, status, connected_by))
                if self.headset_id != '' and self.headset_id == hs_id:
                    found_headset = True
                    headset_status = status

            if len(self.headset_list) == 0:
                warnings.warn("No headset available. Please turn on a headset.")
            elif self.headset_id == '':
                # set first headset is default headset
                self.headset_id = self.headset_list[0]['id']
                # call query headet again
                self.query_headset()
            elif found_headset == False:
                warnings.warn("Can not found the headset " + self.headset_id + ". Please make sure the id is correct.")
            elif found_headset == True:
                if headset_status == 'connected':
                    # create session with the headset
                    self.create_session()
                elif headset_status == 'discovered':
                    self.connect_headset(self.headset_id)
                elif headset_status == 'connecting':
                    # wait 3 seconds and query headset again
                    time.sleep(3)
                    self.query_headset()
                else:
                    warnings.warn('query_headset resp: Invalid connection status ' + headset_status)
        elif req_id == CREATE_SESSION_ID:
            self.session_id = result_dic['id']
            print("The session " + self.session_id + " is created successfully.")
            self.emit('create_session_done', data=self.session_id)
        elif req_id == SUB_REQUEST_ID:
            # handle data label
            for stream in result_dic['success']:
                stream_name = stream['streamName']
                stream_labels = stream['cols']
                print('The data stream '+ stream_name + ' is subscribed successfully.')
                # ignore com, fac and sys data label because they are handled in on_new_data
                if stream_name != 'com' and stream_name != 'fac':
                    self.extract_data_labels(stream_name, stream_labels)
                self.emit('stream_sub_done')

            for stream in result_dic['failure']:
                stream_name = stream['streamName']
                stream_msg = stream['message']
                print('The data stream '+ stream_name + ' is subscribed unsuccessfully. Because: ' + stream_msg)
        elif req_id == UNSUB_REQUEST_ID:
            for stream in result_dic['success']:
                stream_name = stream['streamName']
                print('The data stream '+ stream_name + ' is unsubscribed successfully.')

            for stream in result_dic['failure']:
                stream_name = stream['streamName']
                stream_msg = stream['message']
                print('The data stream '+ stream_name + ' is unsubscribed unsuccessfully. Because: ' + stream_msg)

        elif req_id == QUERY_PROFILE_ID:
            profile_list = []
            for ele in result_dic:
                name = ele['name']
                profile_list.append(name)
            self.emit('query_profile_done', data=profile_list)
        elif req_id == SETUP_PROFILE_ID:
            action = result_dic['action']
            if action == 'create':
                profile_name = result_dic['name']
                if profile_name == self.profile_name:
                    # load profile
                    self.setup_profile(profile_name, 'load')
            elif action == 'load':
                print('load profile successfully')
                self.emit('load_unload_profile_done', isLoaded=True)
            elif action == 'unload':
                self.emit('load_unload_profile_done', isLoaded=False)
            elif action == 'save':
                self.emit('save_profile_done')
        elif req_id == GET_CURRENT_PROFILE_ID:
            print(result_dic)
            name = result_dic['name']
            if name is None:
                # no profile loaded with the headset
                print('get_current_profile: no profile loaded with the headset ' + self.headset_id)
                self.setup_profile(self.profile_name, 'load')
            else:
                loaded_by_this_app = result_dic['loadedByThisApp']
                print('get current profile rsp: ' + name + ", loadedByThisApp: " + str(loaded_by_this_app))
                if name != self.profile_name:
                    warnings.warn("There is profile " + name + " is loaded for headset " + self.headset_id)
                elif loaded_by_this_app == True:
                    self.emit('load_unload_profile_done', isLoaded=True)
                else:
                    self.setup_profile(self.profile_name, 'unload')
                    # warnings.warn("The profile " + name + " is loaded by other applications")
        elif req_id == DISCONNECT_HEADSET_ID:
            print("Disconnect headset " + self.headset_id)
            self.headset_id = ''
        elif req_id == MENTAL_COMMAND_ACTIVE_ACTION_ID:
            self.emit('get_mc_active_action_done', data=result_dic)
        elif req_id == MENTAL_COMMAND_TRAINING_THRESHOLD:
            self.emit('mc_training_threshold_done', data=result_dic)
        elif req_id == MENTAL_COMMAND_BRAIN_MAP_ID:
            self.emit('mc_brainmap_done', data=result_dic)
        elif req_id == SENSITIVITY_REQUEST_ID:
            self.emit('mc_action_sensitivity_done', data=result_dic)
        elif req_id == CREATE_RECORD_REQUEST_ID:
            self.record_id = result_dic['record']['uuid']
            self.emit('create_record_done', data=result_dic['record'])
        elif req_id == STOP_RECORD_REQUEST_ID:
            self.emit('stop_record_done', data=result_dic['record'])
        elif req_id == EXPORT_RECORD_ID:
            # handle data label
            success_export = []
            for record in result_dic['success']:
                record_id = record['recordId']
                success_export.append(record_id)

            for record in result_dic['failure']:
                record_id = record['recordId']
                failure_msg = record['message']
                print('export_record resp failure cases: '+ record_id + ":" + failure_msg)

            self.emit('export_record_done', data=success_export)
        elif req_id == INJECT_MARKER_REQUEST_ID:
            self.emit('inject_marker_done', data=result_dic['marker'])
        elif req_id == INJECT_MARKER_REQUEST_ID:
            self.emit('update_marker_done', data=result_dic['marker'])
        else:
            print('No handling for response of request ' + str(req_id))

    def handle_error(self, recv_dic):
        req_id = recv_dic['id']
        print('handle_error: request Id ' + str(req_id))
        self.emit('inform_error', error_data=recv_dic['error'])

    def handle_warning(self, warning_dic):

        if self.debug:
            print(warning_dic)
        warning_code = warning_dic['code']
        warning_msg = warning_dic['message']
        if warning_code == ACCESS_RIGHT_GRANTED:
            # call authorize again
            self.authorize()
        elif warning_code == HEADSET_CONNECTED:
            # query headset again then create session
            self.query_headset()
        elif warning_code == CORTEX_AUTO_UNLOAD_PROFILE:
            self.profile_name = ''
        elif  warning_code == CORTEX_STOP_ALL_STREAMS:
            # print(warning_msg['behavior'])
            session_id = warning_msg['sessionId']
            if session_id == self.session_id:
                self.emit('warn_cortex_stop_all_sub', data=session_id)
                self.session_id = ''
    
    def handle_stream_data(self, result_dic):
        if result_dic.get('com') != None:
            com_data = {}
            com_data['action'] = result_dic['com'][0]
            com_data['power'] = result_dic['com'][1]
            com_data['time'] = result_dic['time']   
            self.emit('new_com_data', data=com_data)
        elif result_dic.get('fac') != None:
            fe_data = {}
            fe_data['eyeAct'] = result_dic['fac'][0]    #eye action
            fe_data['uAct'] = result_dic['fac'][1]      #upper action
            fe_data['uPow'] = result_dic['fac'][2]      #upper action power
            fe_data['lAct'] = result_dic['fac'][3]      #lower action
            fe_data['lPow'] = result_dic['fac'][4]      #lower action power
            fe_data['time'] = result_dic['time']
            self.emit('new_fe_data', data=fe_data)
        elif result_dic.get('eeg') != None:
            eeg_data = {}
            eeg_data['eeg'] = result_dic['eeg']
            eeg_data['eeg'].pop() # remove markers
            eeg_data['time'] = result_dic['time']
            self.emit('new_eeg_data', data=eeg_data)
        elif result_dic.get('mot') != None:
            mot_data = {}
            mot_data['mot'] = result_dic['mot']
            mot_data['time'] = result_dic['time']
            self.emit('new_mot_data', data=mot_data)
        elif result_dic.get('dev') != None:
            dev_data = {}
            dev_data['signal'] = result_dic['dev'][1]
            dev_data['dev'] = result_dic['dev'][2]
            dev_data['batteryPercent'] = result_dic['dev'][3]
            dev_data['time'] = result_dic['time']
            self.emit('new_dev_data', data=dev_data)
        elif result_dic.get('met') != None:
            met_data = {}
            met_data['met'] = result_dic['met']
            met_data['time'] = result_dic['time']
            self.emit('new_met_data', data=met_data)
        elif result_dic.get('pow') != None:
            pow_data = {}
            pow_data['pow'] = result_dic['pow']
            pow_data['time'] = result_dic['time']
            self.emit('new_pow_data', data=pow_data)
        elif result_dic.get('sys') != None:
            sys_data = result_dic['sys']
            self.emit('new_sys_data', data=sys_data)
        else :
            print(result_dic)
    
    def on_message(self, *args):
        recv_dic = json.loads(args[1])
        if 'sid' in recv_dic:
            self.handle_stream_data(recv_dic)
        elif 'result' in recv_dic:
            self.handle_result(recv_dic)
        elif 'error' in recv_dic:
            self.handle_error(recv_dic)
        elif 'warning' in recv_dic:
            self.handle_warning(recv_dic['warning'])
        else:
            raise KeyError

     # Server Requests

    def query_headset(self):
        print('query headset --------------------------------')
        query_headset_request = {
            "jsonrpc": "2.0", 
            "id": QUERY_HEADSET_ID,
            "method": "queryHeadsets",
            "params": {}
        }
        if self.debug:
            print('queryHeadsets request \n', json.dumps(query_headset_request, indent=4))

        self.ws.send(json.dumps(query_headset_request, indent=4))

    def connect_headset(self, headset_id):
        print('connect headset --------------------------------')
        connect_headset_request = {
            "jsonrpc": "2.0", 
            "id": CONNECT_HEADSET_ID,
            "method": "controlDevice",
            "params": {
                "command": "connect",
                "headset": headset_id
            }
        }
        if self.debug:
            print('controlDevice request \n', json.dumps(connect_headset_request, indent=4))

        self.ws.send(json.dumps(connect_headset_request, indent=4))

    def request_access(self):
        print('request access --------------------------------')
        request_access_request = {
            "jsonrpc": "2.0", 
            "method": "requestAccess",
            "params": {
                "clientId": self.client_id, 
                "clientSecret": self.client_secret
            },
            "id": REQUEST_ACCESS_ID
        }

        self.ws.send(json.dumps(request_access_request, indent=4))

    def has_access_right(self):
        print('check has access right --------------------------------')
        has_access_request = {
            "jsonrpc": "2.0", 
            "method": "hasAccessRight",
            "params": {
                "clientId": self.client_id, 
                "clientSecret": self.client_secret
            },
            "id": HAS_ACCESS_RIGHT_ID
        }
        self.ws.send(json.dumps(has_access_request, indent=4))

    def authorize(self):
        print('authorize --------------------------------')
        authorize_request = {
            "jsonrpc": "2.0",
            "method": "authorize", 
            "params": { 
                "clientId": self.client_id, 
                "clientSecret": self.client_secret, 
                "license": self.license,
                "debit": self.debit
            },
            "id": AUTHORIZE_ID
        }

        if self.debug:
            print('auth request \n', json.dumps(authorize_request, indent=4))

        self.ws.send(json.dumps(authorize_request))

    def create_session(self):
        if self.session_id != '':
            warnings.warn("There is existed session " + self.session_id)
            return

        print('create session --------------------------------')
        create_session_request = { 
            "jsonrpc": "2.0",
            "id": CREATE_SESSION_ID,
            "method": "createSession",
            "params": {
                "cortexToken": self.auth,
                "headset": self.headset_id,
                "status": "active"
            }
        }
        
        if self.debug:
            print('create session request \n', json.dumps(create_session_request, indent=4))

        self.ws.send(json.dumps(create_session_request))

    def close_session(self):
        print('close session --------------------------------')
        close_session_request = { 
            "jsonrpc": "2.0",
            "id": CREATE_SESSION_ID,
            "method": "updateSession",
            "params": {
                "cortexToken": self.auth,
                "session": self.session_id,
                "status": "close"
            }
        }

        self.ws.send(json.dumps(close_session_request))

    def get_cortex_info(self):
        print('get cortex version --------------------------------')
        get_cortex_info_request = {
            "jsonrpc": "2.0",
            "method": "getCortexInfo",
            "id":GET_CORTEX_INFO_ID
        }

        self.ws.send(json.dumps(get_cortex_info_request))

    """
        Prepare steps include:
        Step 1: check access right. If user has not granted for the application, requestAccess will be called
        Step 2: authorize: to generate a Cortex access token which is required parameter of many APIs
        Step 3: Connect a headset. If no wanted headet is set, the first headset in the list will be connected.
                If you use EPOC Flex headset, you should connect the headset with a proper mappings via EMOTIV Launcher first 
        Step 4: Create a working session with the connected headset
        Returns
        -------
        None
        """

    def do_prepare_steps(self):
        print('do_prepare_steps--------------------------------')
        # check access right
        self.has_access_right()

    def disconnect_headset(self):
        print('disconnect headset --------------------------------')
        disconnect_headset_request = {
            "jsonrpc": "2.0", 
            "id": DISCONNECT_HEADSET_ID,
            "method": "controlDevice",
            "params": {
                "command": "disconnect",
                "headset": self.headset_id
            }
        }

        self.ws.send(json.dumps(disconnect_headset_request))

    def sub_request(self, stream):
        print('subscribe request --------------------------------')
        sub_request_json = {
            "jsonrpc": "2.0", 
            "method": "subscribe", 
            "params": { 
                "cortexToken": self.auth,
                "session": self.session_id,
                "streams": stream
            }, 
            "id": SUB_REQUEST_ID
        }
        if self.debug:
            print('subscribe request \n', json.dumps(sub_request_json, indent=4))

        self.ws.send(json.dumps(sub_request_json))

    def unsub_request(self, stream):
        print('unsubscribe request --------------------------------')
        unsub_request_json = {
            "jsonrpc": "2.0", 
            "method": "unsubscribe", 
            "params": { 
                "cortexToken": self.auth,
                "session": self.session_id,
                "streams": stream
            }, 
            "id": UNSUB_REQUEST_ID
        }
        if self.debug:
            print('unsubscribe request \n', json.dumps(unsub_request_json, indent=4))

        self.ws.send(json.dumps(unsub_request_json))

    def extract_data_labels(self, stream_name, stream_cols):
        labels = {}
        labels['streamName'] = stream_name

        data_labels = []
        if stream_name == 'eeg':
            # remove MARKERS
            data_labels = stream_cols[:-1]
        elif stream_name == 'dev':
            # get cq header column except battery, signal and battery percent
            data_labels = stream_cols[2]
        else:
            data_labels = stream_cols

        labels['labels'] = data_labels
        print(labels)
        self.emit('new_data_labels', data=labels)

    def query_profile(self):
        print('query profile --------------------------------')
        query_profile_json = {
            "jsonrpc": "2.0",
            "method": "queryProfile",
            "params": {
              "cortexToken": self.auth,
            },
            "id": QUERY_PROFILE_ID
        }

        if self.debug:
            print('query profile request \n', json.dumps(query_profile_json, indent=4))
            print('\n')

        self.ws.send(json.dumps(query_profile_json))

    def get_current_profile(self):
        print('get current profile:')
        get_profile_json = {
            "jsonrpc": "2.0",
            "method": "getCurrentProfile",
            "params": {
              "cortexToken": self.auth,
              "headset": self.headset_id,
            },
            "id": GET_CURRENT_PROFILE_ID
        }
        
        if self.debug:
            print('get current profile json:\n', json.dumps(get_profile_json, indent=4))
            print('\n')

        self.ws.send(json.dumps(get_profile_json))

    def setup_profile(self, profile_name, status):
        print('setup profile: ' + status + ' -------------------------------- ')
        setup_profile_json = {
            "jsonrpc": "2.0",
            "method": "setupProfile",
            "params": {
              "cortexToken": self.auth,
              "headset": self.headset_id,
              "profile": profile_name,
              "status": status
            },
            "id": SETUP_PROFILE_ID
        }
        
        if self.debug:
            print('setup profile json:\n', json.dumps(setup_profile_json, indent=4))
            print('\n')

        self.ws.send(json.dumps(setup_profile_json))

    def train_request(self, detection, action, status):
        print('train request --------------------------------')
        train_request_json = {
            "jsonrpc": "2.0", 
            "method": "training", 
            "params": {
              "cortexToken": self.auth,
              "detection": detection,
              "session": self.session_id,
              "action": action,
              "status": status
            }, 
            "id": TRAINING_ID
        }
        if self.debug:
            print('training request:\n', json.dumps(train_request_json, indent=4))
            print('\n')

        self.ws.send(json.dumps(train_request_json))

    def create_record(self, title, **kwargs):
        print('create record --------------------------------')

        if (len(title) == 0):
            warnings.warn('Empty record_title. Please fill the record_title before running script.')
            # close socket
            self.close()
            return

        params_val = {"cortexToken": self.auth, "session": self.session_id, "title": title}

        for key, value in kwargs.items():
            params_val.update({key: value})

        create_record_request = {
            "jsonrpc": "2.0", 
            "method": "createRecord",
            "params": params_val, 
            "id": CREATE_RECORD_REQUEST_ID
        }
        if self.debug:
            print('create record request:\n', json.dumps(create_record_request, indent=4))

        self.ws.send(json.dumps(create_record_request))

    def stop_record(self):
        print('stop record --------------------------------')
        stop_record_request = {
            "jsonrpc": "2.0", 
            "method": "stopRecord",
            "params": {
                "cortexToken": self.auth,
                "session": self.session_id
            }, 

            "id": STOP_RECORD_REQUEST_ID
        }
        if self.debug:
            print('stop record request:\n', json.dumps(stop_record_request, indent=4))
        self.ws.send(json.dumps(stop_record_request))

    def export_record(self, folder, stream_types, export_format, record_ids,
                      version, **kwargs):
        print('export record --------------------------------: ')
        #validate destination folder
        if (len(folder) == 0):
            warnings.warn('Invalid folder parameter. Please set a writable destination folder for exporting data.')
            # close socket
            self.close()
            return

        params_val = {"cortexToken": self.auth, 
                      "folder": folder,
                      "format": export_format,
                      "streamTypes": stream_types,
                      "recordIds": record_ids}

        if export_format == 'CSV':
            params_val.update({'version': version})

        for key, value in kwargs.items():
            params_val.update({key: value})

        export_record_request = {
            "jsonrpc": "2.0",
            "id":EXPORT_RECORD_ID,
            "method": "exportRecord", 
            "params": params_val
        }

        if self.debug:
            print('export record request \n',
                json.dumps(export_record_request, indent=4))
        
        self.ws.send(json.dumps(export_record_request))

    def inject_marker_request(self, time, value, label, **kwargs):
        print('inject marker --------------------------------')
        params_val = {"cortexToken": self.auth, 
                      "session": self.session_id, 
                      "time": time,
                      "value": value,
                      "label":label}

        for key, value in kwargs.items():
            params_val.update({key: value})

        inject_marker_request = {
            "jsonrpc": "2.0",
            "id": INJECT_MARKER_REQUEST_ID,
            "method": "injectMarker", 
            "params": params_val
        }
        if self.debug:
            print('inject marker request \n', json.dumps(inject_marker_request, indent=4))
        self.ws.send(json.dumps(inject_marker_request))

    def update_marker_request(self, markerId, time, **kwargs):
        print('update marker --------------------------------')
        params_val = {"cortexToken": self.auth, 
                      "session": self.session_id,
                      "markerId": markerId,
                      "time": time}

        for key, value in kwargs.items():
            params_val.update({key: value})

        update_marker_request = {
            "jsonrpc": "2.0",
            "id": UPDATE_MARKER_REQUEST_ID,
            "method": "updateMarker", 
            "params": params_val
        }
        if self.debug:
            print('update marker request \n', json.dumps(update_marker_request, indent=4))
        self.ws.send(json.dumps(update_marker_request))

    def get_mental_command_action_sensitivity(self, profile_name):
        print('get mental command sensitivity ------------------')
        sensitivity_request = {
            "id": SENSITIVITY_REQUEST_ID,
            "jsonrpc": "2.0",
            "method": "mentalCommandActionSensitivity",
            "params": {
                "cortexToken": self.auth,
                "profile": profile_name,
                "status": "get"
            }
        }
        if self.debug:
            print('get mental command sensitivity \n', json.dumps(sensitivity_request, indent=4))

        self.ws.send(json.dumps(sensitivity_request))

    def set_mental_command_action_sensitivity(self, profile_name, values):
        print('set mental command sensitivity ------------------')
        sensitivity_request = {
                                "id": SENSITIVITY_REQUEST_ID,
                                "jsonrpc": "2.0",
                                "method": "mentalCommandActionSensitivity",
                                "params": {
                                    "cortexToken": self.auth,
                                    "profile": profile_name,
                                    "session": self.session_id,
                                    "status": "set",
                                    "values": values
                                }
                            }
        if self.debug:
            print('set mental command sensitivity \n', json.dumps(sensitivity_request, indent=4))
            
        self.ws.send(json.dumps(sensitivity_request))

    def get_mental_command_active_action(self, profile_name):
        print('get mental command active action ------------------')
        command_active_request = {
            "id": MENTAL_COMMAND_ACTIVE_ACTION_ID,
            "jsonrpc": "2.0",
            "method": "mentalCommandActiveAction",
            "params": {
                "cortexToken": self.auth,
                "profile": profile_name,
                "status": "get"
            }
        }
        if self.debug:
            print('get mental command active action \n', json.dumps(command_active_request, indent=4))

        self.ws.send(json.dumps(command_active_request))

    def set_mental_command_active_action(self, actions):
        print('set mental command active action ------------------')
        command_active_request = {
            "id": SET_MENTAL_COMMAND_ACTIVE_ACTION_ID,
            "jsonrpc": "2.0",
            "method": "mentalCommandActiveAction",
            "params": {
                "cortexToken": self.auth,
                "session": self.session_id,
                "status": "set",
                "actions": actions
            }
        }

        if self.debug:
            print('set mental command active action \n', json.dumps(command_active_request, indent=4))

        self.ws.send(json.dumps(command_active_request))

    def get_mental_command_brain_map(self, profile_name):
        print('get mental command brain map ------------------')
        brain_map_request = {
            "id": MENTAL_COMMAND_BRAIN_MAP_ID,
            "jsonrpc": "2.0",
            "method": "mentalCommandBrainMap",
            "params": {
                "cortexToken": self.auth,
                "profile": profile_name,
                "session": self.session_id
            }
        }
        if self.debug:
            print('get mental command brain map \n', json.dumps(brain_map_request, indent=4))
        self.ws.send(json.dumps(brain_map_request))

    def get_mental_command_training_threshold(self, profile_name):
        print('get mental command training threshold -------------')
        training_threshold_request = {
            "id": MENTAL_COMMAND_TRAINING_THRESHOLD,
            "jsonrpc": "2.0",
            "method": "mentalCommandTrainingThreshold",
            "params": {
                "cortexToken": self.auth,
                "session": self.session_id
            }
        }
        if self.debug:
            print('get mental command training threshold \n', json.dumps(training_threshold_request, indent=4))
        self.ws.send(json.dumps(training_threshold_request))

# -------------------------------------------------------------------
# -------------------------------------------------------------------
# -------------------------------------------------------------------

class App(object):

    def __init__(self, app_client_id, app_client_secret, **kwargs):
        print("App __init__")
        self.c = Connect(app_client_id, app_client_secret, debug_mode= False, **kwargs)
        self.streams = []
        self.profile_name = ''

        self.loop = asyncio.get_event_loop()
        self.event_received = asyncio.Event()

        self.c.bind(new_data_labels=self.on_new_data_labels)

        self.c.bind(query_profile_done=self.on_query_profile_done)
        self.c.bind(load_unload_profile_done=self.on_load_unload_profile_done)
        self.c.bind(save_profile_done=self.on_save_profile_done)
        #self.c.bind(new_com_data=self.on_new_com_data)
        self.c.bind(get_mc_active_action_done=self.on_get_mc_active_action_done)
        self.c.bind(mc_action_sensitivity_done=self.on_mc_action_sensitivity_done)
        
        self.c.bind(inform_error=self.on_inform_error)

        self.input()
        
    def start(self, profile_name, headsetId=''):

        if profile_name == '':
            raise ValueError(' Empty profile_name. The profile_name cannot be empty.')
        
        self.profile_name = profile_name
        self.c.set_wanted_profile(profile_name)
        
        if headsetId != '':
            self.c.set_wanted_headset(headsetId)
        
        self.c.open()

    def sub(self, streams):
        """
        To subscribe to one or more data streams
        'eeg': EEG
        'mot' : Motion
        'dev' : Device information
        'met' : Performance metric
        'pow' : Band power

        Parameters
        ----------
        streams : list, required
            list of streams. For example, ['eeg', 'mot']

        Returns
        -------
        None
        """
        self.c.sub_request(streams)

    def load_profile(self, profile_name):
        """
        To load a profile

        Parameters
        ----------
        profile_name : str, required
            profile name

        Returns
        -------
        None
        """
        self.c.setup_profile(profile_name, 'load')

    def unload_profile(self, profile_name):
        """
        To unload a profile
        Parameters
        ----------
        profile_name : str, required
            profile name

        Returns
        -------
        None
        """
        self.c.setup_profile(profile_name, 'unload')

    def save_profile(self, profile_name):
        """
        To save a profile

        Parameters
        ----------
        profile_name : str, required
            profile name

        Returns
        -------
        None
        """
        self.c.setup_profile(profile_name, 'save')

    def unsub(self, streams):
        """
        To unsubscribe to one or more data streams
        'eeg': EEG
        'mot' : Motion
        'dev' : Device information
        'met' : Performance metric
        'pow' : Band power

        Parameters
        ----------
        streams : list, required
            list of streams. For example, ['eeg', 'mot']

        Returns
        -------
        None
        """
        self.c.unsub_request(streams)

    def get_active_action(self, profile_name):
        """
        To get active actions for the mental command detection.
        Maximum 4 mental command actions are actived. This doesn't include "neutral"

        Parameters
        ----------
        profile_name : str, required
            profile name

        Returns
        -------
        None
        """
        self.c.get_mental_command_active_action(profile_name)

    def get_sensitivity(self, profile_name):
        """
        To get the sensitivity of the 4 active mental command actions. This doesn't include "neutral"
        It will return arrays of 4 numbers, range 1 - 10
        The order of the values must follow the order of the active actions, as returned by mentalCommandActiveAction
        If the number of active actions < 4, the rest numbers are ignored.

        Parameters
        ----------
        profile_name : str, required
            profile name

        Returns
        -------
        None
        """
        self.c.get_mental_command_action_sensitivity(profile_name)

    def set_sensitivity(self, profile_name, values):
        """
        To set the sensitivity of the 4 active mental command actions. This doesn't include "neutral".
        The order of the values must follow the order of the active actions, as returned by mentalCommandActiveAction
        
        Parameters
        ----------
        profile_name : str, required
            profile name
        values: list, required
            list of sensitivity values. The range is from 1 (lowest sensitivy) - 10 (higest sensitivity)
            For example: [neutral, push, pull, lift, drop] -> sensitivity [7, 8, 3, 6] <=> push : 7 , pull: 8, lift: 3, drop:6
                         [neutral, push, pull] -> sensitivity [7, 8, 5, 5] <=> push : 7 , pull: 8  , others resvered


        Returns
        -------
        None
        """
        self.c.set_mental_command_action_sensitivity(profile_name, values)

    def handle_command(self, command):
        
        def streams_bind():
            self.c.bind(new_eeg_data=self.on_new_eeg_data)
            self.c.bind(new_mot_data=self.on_new_mot_data)
            self.c.bind(new_dev_data=self.on_new_dev_data)
            self.c.bind(new_met_data=self.on_new_met_data)
            self.c.bind(new_pow_data=self.on_new_pow_data)
        def streams_unbind():
            self.c.unbind(self.on_new_eeg_data)
            self.c.unbind(self.on_new_mot_data)
            self.c.unbind(self.on_new_dev_data)
            self.c.unbind(self.on_new_met_data)
            self.c.unbind(self.on_new_pow_data)

        if command == 'open':
            if self.c.session_id == '':
                self.profile_name = input("Please enter a profile name: ")
                self.start(self.profile_name)
                self.c.bind_async(self.loop, create_session_done = self.receive_message)
                self.loop.run_until_complete(self.wait_for_event())
                self.c.unbind(self.receive_message)
            else:
                print(f"Session: {self.c.session_id} already active")

        elif command == 'close':
            self.c.close()

        # Stream
        elif command == 'stream':
            streams_input = input("What streams would you like to use: ")
            streams = list(streams_input.split(','))
            for i, stream in enumerate(streams):
                streams[i] = stream.strip()
            self.streams = streams
            self.sub(self.streams)
            
            self.c.bind_async(self.loop, stream_sub_done = self.receive_message)
            self.loop.run_until_complete(self.wait_for_event())
            self.c.unbind(self.receive_message)

        elif command == 'display stream data':
            streams_bind()
            time.sleep(2)
            streams_unbind()

        elif command == 'stop stream':
            self.unsub(self.streams)
            self.streams = []

        # Stream training data (train on EMOTIVBCI first)

        elif command == 'train':
            self.c.query_profile()

        elif command == 'display train data':
            self.c.bind(new_com_data=self.on_new_com_data)
            time.sleep(2)
            self.c.unbind(self.on_new_com_data)

        # Quit

        elif command == 'stop display':
            streams_unbind()
            self.c.unbind(self.on_new_com_data)

        elif command == '':
            pass

        else:
            print("Invalid command")

        
    def input(self):
        command = ''
        while command != "close":
            command = input("Enter a command: ")
            self.handle_command(command)

    # Handle Stream Data

    def on_new_data_labels(self, *args, **kwargs):
        """
        To handle data labels of subscribed data 
        Returns
        -------
        data: list  
              array of data labels
        name: stream name
        For example:
            eeg: ["COUNTER","INTERPOLATED", "AF3", "T7", "Pz", "T8", "AF4", "RAW_CQ", "MARKER_HARDWARE"]
            motion: ['COUNTER_MEMS', 'INTERPOLATED_MEMS', 'Q0', 'Q1', 'Q2', 'Q3', 'ACCX', 'ACCY', 'ACCZ', 'MAGX', 'MAGY', 'MAGZ']
            dev: ['AF3', 'T7', 'Pz', 'T8', 'AF4', 'OVERALL']
            met : ['eng.isActive', 'eng', 'exc.isActive', 'exc', 'lex', 'str.isActive', 'str', 'rel.isActive', 'rel', 'int.isActive', 'int', 'foc.isActive', 'foc']
            pow: ['AF3/theta', 'AF3/alpha', 'AF3/betaL', 'AF3/betaH', 'AF3/gamma', 'T7/theta', 'T7/alpha', 'T7/betaL', 'T7/betaH', 'T7/gamma', 'Pz/theta', 'Pz/alpha', 'Pz/betaL', 'Pz/betaH', 'Pz/gamma', 'T8/theta', 'T8/alpha', 'T8/betaL', 'T8/betaH', 'T8/gamma', 'AF4/theta', 'AF4/alpha', 'AF4/betaL', 'AF4/betaH', 'AF4/gamma']
        """
        data = kwargs.get('data')
        stream_name = data['streamName']
        stream_labels = data['labels']
        print('{} labels are : {}'.format(stream_name, stream_labels))

    def on_new_eeg_data(self, *args, **kwargs):
        """
        To handle eeg data emitted from Cortex

        Returns
        -------
        data: dictionary
             The values in the array eeg match the labels in the array labels return at on_new_data_labels
        For example:
           {'eeg': [99, 0, 4291.795, 4371.795, 4078.461, 4036.41, 4231.795, 0.0, 0], 'time': 1627457774.5166}
        """
        data = kwargs.get('data')
        print('eeg data: {}'.format(data))

    def on_new_mot_data(self, *args, **kwargs):
        """
        To handle motion data emitted from Cortex

        Returns
        -------
        data: dictionary
             The values in the array motion match the labels in the array labels return at on_new_data_labels
        For example: {'mot': [33, 0, 0.493859, 0.40625, 0.46875, -0.609375, 0.968765, 0.187503, -0.250004, -76.563667, -19.584995, 38.281834], 'time': 1627457508.2588}
        """
        data = kwargs.get('data')
        print('motion data: {}'.format(data))

    def on_new_dev_data(self, *args, **kwargs):
        """
        To handle dev data emitted from Cortex

        Returns
        -------
        data: dictionary
             The values in the array dev match the labels in the array labels return at on_new_data_labels
        For example:  {'signal': 1.0, 'dev': [4, 4, 4, 4, 4, 100], 'batteryPercent': 80, 'time': 1627459265.4463}
        """
        data = kwargs.get('data')
        print('dev data: {}'.format(data))

    def on_new_met_data(self, *args, **kwargs):
        """
        To handle performance metrics data emitted from Cortex

        Returns
        -------
        data: dictionary
             The values in the array met match the labels in the array labels return at on_new_data_labels
        For example: {'met': [True, 0.5, True, 0.5, 0.0, True, 0.5, True, 0.5, True, 0.5, True, 0.5], 'time': 1627459390.4229}
        """
        data = kwargs.get('data')
        print('pm data: {}'.format(data))

    def on_new_pow_data(self, *args, **kwargs):
        """
        To handle band power data emitted from Cortex

        Returns
        -------
        data: dictionary
             The values in the array pow match the labels in the array labels return at on_new_data_labels
        For example: {'pow': [5.251, 4.691, 3.195, 1.193, 0.282, 0.636, 0.929, 0.833, 0.347, 0.337, 7.863, 3.122, 2.243, 0.787, 0.496, 5.723, 2.87, 3.099, 0.91, 0.516, 5.783, 4.818, 2.393, 1.278, 0.213], 'time': 1627459390.1729}
        """
        data = kwargs.get('data')
        print('pow data: {}'.format(data))

    def on_new_com_data(self, *args, **kwargs):
        """
        To handle mental command data emitted from Cortex
        
        Returns
        -------
        data: dictionary
             the format such as {'action': 'neutral', 'power': 0.0, 'time': 1590736942.8479}
        """
        data = kwargs.get('data')
        print('mc data: {}'.format(data))

    # Callbacks
    async def receive_message(self, *args, **kwargs):
        self.event_received.set()

    async def wait_for_event(self):
        await self.event_received.wait()
        self.event_received.clear()
    
    def on_inform_error(self, *args, **kwargs):
        error_data = kwargs.get('error_data')
        print(error_data)

    def on_query_profile_done(self, *args, **kwargs):
        print('on_query_profile_done')
        self.profile_lists = kwargs.get('data')
        if self.profile_name in self.profile_lists:
            # the profile is existed
            self.c.get_current_profile()
        else:
            # create profile
            self.c.setup_profile(self.profile_name, 'create')

    def on_load_unload_profile_done(self, *args, **kwargs):
        is_loaded = kwargs.get('isLoaded')
        print("on_load_unload_profile_done: " + str(is_loaded))
        
        if is_loaded == True:
            # get active action
            self.get_active_action(self.profile_name)
        else:
            print('The profile ' + self.profile_name + ' is unloaded')
            self.profile_name = ''

    def on_save_profile_done (self, *args, **kwargs):
        print('Save profile ' + self.profile_name + " successfully")
        # subscribe mental command data
        stream = ['com']
        self.c.sub_request(stream)

    def on_get_mc_active_action_done(self, *args, **kwargs):
        data = kwargs.get('data')
        print('on_get_mc_active_action_done: {}'.format(data))
        self.get_sensitivity(self.profile_name)

    def on_mc_action_sensitivity_done(self, *args, **kwargs):
        data = kwargs.get('data')
        print('on_mc_action_sensitivity_done: {}'.format(data))
        if isinstance(data, list):
            # get sensivity
            new_values = [7,7,5,5]
            self.set_sensitivity(self.profile_name, new_values)
        else:
            # set sensitivity done -> save profile
            self.save_profile(self.profile_name)


def main():
    
    your_app_client_id = "QDjTb3H1Sq1MIKBuoFznQgX8FFTGkZDcIzPeeXfR"
    your_app_client_secret = "ODD0Oey9ck9HLiQ2g5cpx9TYarnFeuSgjWlsKwKkYbcbjWmyagxiEbFMX45bgqvkfcXmdnEFh3xOZXbrxvhnBeN4ykT5wFUpi2mYYvuiSwEDzAKrGdCzhLzUHijRQUmG"

    client = App(your_app_client_id, your_app_client_secret)

if __name__ =='__main__':
    main()
