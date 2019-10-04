from netmiko import ConnectHandler


#######################################################################################
# ------------------------------ classes part ----------------------------------------#
#######################################################################################


class CiscoXR:

    def __init__(self, ip, host):
        self.hostname = host
        self.ip_address = ip
        self.os_type = "cisco_xr"
        self.ssh_conn = None

        self.connection_status = True           # failed connection status, False if connection fails
        self.connection_error_msg = None        # connection error message

        self.show_platform_log = None
        self.show_inf_summary_log = None
        self.show_inf_description_log = None
        self.uplink = 0
        self.local = 0

        self.description_all = []
        self.description_exc_updown = []
        self.description_short = []

        self.platform = {"0/0/CPU0": "N/A",
                         "0/0/0": "N/A",
                         "0/0/1": "N/A",
                         "0/1/CPU0": "N/A",
                         "0/1/0": "N/A",
                         "0/1/1": "N/A",
                         "0/2/CPU0": "N/A",
                         "0/2/0": "N/A",
                         "0/2/1": "N/A",
                         "0/3/CPU0": "N/A",
                         "0/3/0": "N/A",
                         "0/3/1": "N/A",
                         "0/4/CPU0": "N/A",
                         "0/4/0": "N/A",
                         "0/4/1": "N/A",
                         "0/5/CPU0": "N/A",
                         "0/5/0": "N/A",
                         "0/5/1": "N/A",
                         "0/6/CPU0": "N/A",
                         "0/6/0": "N/A",
                         "0/6/1": "N/A",
                         "0/7/CPU0": "N/A",
                         "0/7/0": "N/A",
                         "0/7/1": "N/A"}

        self.tengig = {"total": None,
                       "up": None,
                       "down": None,
                       "admin down": None,
                       "total_description": 0,
                       "down_description": 0}

        self.show_errors = {"show_platform": 0,
                            "show_inf_summary": 0,
                            "show_inf_description": 0}

    def connect(self, myusername, mypassword):
        self.ssh_conn = ConnectHandler(device_type=self.os_type,
                                       ip=self.ip_address,
                                       username=myusername,
                                       password=mypassword)

    def disconnect(self):
        self.ssh_conn.disconnect()

    def show_platform(self):
        self.show_platform_log = self.ssh_conn.send_command(r"show platform")

    def show_inf_summary(self):
        self.show_inf_summary_log = self.ssh_conn.send_command(r"show interfaces summary")

    def show_inf_description(self):
        self.show_inf_description_log = self.ssh_conn.send_command(r"show interfaces description")

    def reset(self):
        self.connection_status = True
        self.connection_error_msg = None
        self.show_platform_log = None
        self.show_inf_summary_log = None
        self.show_inf_description_log = None
