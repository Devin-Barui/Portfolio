from connect import *
import asyncio
import time

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

