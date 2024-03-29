import queue
import os
from sys import argv
from threading import Thread
from deffile import *
from datetime import datetime

starttime = datetime.now()
current_date = starttime.strftime("%Y.%m.%d")
current_time = starttime.strftime("%H.%M.%S")
current_dir = os.getcwd()
folder = "{}\\logs\\{}\\".format(current_dir, current_date)     # current dir / logs / date /

if not os.path.exists(folder):
    os.mkdir(folder)

q = queue.Queue()

#######################################################################################
# ------------------------------ main part -------------------------------------------#
#######################################################################################


argv_dict = get_argv(argv)
username, password = get_user_pw()
devices = get_devinfo("devices.yaml")

total_devices = len(devices)

print("-------------------------------------------------------------------------------------------------------")
print("hostname            ip address                 comment")
print("-------------------------------------------------------------------------------------------------------")


for i in range(argv_dict["maxth"]):

    th = Thread(target=mconnect, args=(username, password, q))
    th.setDaemon(True)
    th.start()


for device in devices:
    q.put(device)

q.join()

print("")

failed_connection_count = write_logs(devices, current_date, current_time, folder, export_device_info, export_excel)
duration = datetime.now() - starttime


#######################################################################################
# ------------------------------ last part -------------------------------------------#
#######################################################################################


print("--------------------------------------------------------------")
print("failed connection: {0}  total device number: {1}".format(failed_connection_count, total_devices))
print("elapsed time: {}".format(duration))
print("--------------------------------------------------------------\n")
