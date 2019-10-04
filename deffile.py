import yaml
import re
import time
from devclass import CiscoXR
from openpyxl import Workbook
from pprint import pformat
from netmiko.ssh_exception import NetMikoTimeoutException
from getpass import getpass


#######################################################################################
# ------------------------------ def function part -----------------------------------#
#######################################################################################


def get_argv(argv):
    argv_dict = {"maxth": 10}
    mt_pattern = re.compile(r"mt([0-9]+)")
    for i in argv:
        if "mt" in i:
            match = re.search(mt_pattern, i)
            if match and int(match.group(1)) <= 100:
                argv_dict["maxth"] = int(match.group(1))

    print("")
    print("max threads: {}".format(argv_dict["maxth"]))
    return argv_dict


def get_user_pw():
    username = input("Enter login: ")
    password = getpass()
    return username, password


def get_devinfo(yaml_file):
    devices = []
    file = open(yaml_file, "r")
    devices_info = yaml.safe_load(file)
    if isinstance(devices_info, dict):
        print("hostname : ip")
        for hostname, ip_address in devices_info.items():
            device = CiscoXR(ip=ip_address, host=hostname)
            devices.append(device)
    elif isinstance(devices_info, list) and "-" in devices_info[0]:    # hostname list
        print("hostname list")
        for hostname in devices_info:
            device = CiscoXR(ip=hostname, host=hostname)
            devices.append(device)
    elif isinstance(devices_info, list) and "-" not in devices_info[0]:  # ip list
        print("ip list")
        for ip_address in devices_info:
            device = CiscoXR(ip=ip_address, host="hostname")
            devices.append(device)

    file.close()
    print("")
    return devices


def mconnect(username, password, q):
    while True:
        device = q.get()
        i = 0
        while True:
            try:
                print("{1:20}{2:25}{0:22}".format("", device.hostname, device.ip_address))
                device.connect(username, password)
                show_commands(device)
                parse_show_platform(device)
                parse_show_inf_summary(device)
                parse_show_inf_description(device)
                count_uplink(device)
                count_inf_description(device)
                device.disconnect()
                q.task_done()
                break

            except NetMikoTimeoutException as err_msg:
                device.connection_status = False
                device.connection_error_msg = str(err_msg)
                print("{0:20}{1:25}{2:20}".format(device.hostname, device.ip_address, "timeout"))
                q.task_done()
                break

            except (Exception, ConnectionResetError) as err_msg:
                if i == 3:
                    device.connection_status = False
                    device.connection_error_msg = str(err_msg)
                    print("{0:20}{1:25}{2:20} i={3}".format(device.hostname, device.ip_address,
                                                            "BREAK connection failed", i))
                    q.task_done()
                    break
                else:
                    i += 1
                    device.reset()
                    print("{0:20}{1:25}{2:20} i={3} msg={4}".format(device.hostname, device.ip_address,
                                                                    "ERROR connection failed", i, err_msg))
                    time.sleep(5)


#######################################################################################
# ------------------------------ logging ---------------------------------------------#
#######################################################################################


def export_device_info(device, export_file):

    export_file.write("#" * 80 + "\n")
    export_file.write("### {} : {} ###\n\n".format(device.hostname, device.ip_address))

    export_file.write("### device.show_platform_log ###\n\n")
    export_file.write(device.show_platform_log)
    export_file.write("\n\n")

    export_file.write("### device.show_inf_summary_log ###\n\n")
    export_file.write(device.show_inf_summary_log)
    export_file.write("\n\n")

    export_file.write("### device.show_inf_description_log ###\n\n")
    export_file.write(device.show_inf_description_log)
    export_file.write("\n\n")

    export_file.write("### device.show_errors ###\n\n")
    export_file.write(pformat(device.show_errors))
    export_file.write("\n\n")


def write_logs(devices, current_date, current_time, folder, exp_devinfo, exp_excel):
    failed_connection_count = 0
    exp_excel(devices, current_time, folder)

    conn_msg_filename = "{}{}_connection_error_msg.txt".format(folder, current_time)
    conn_msg_filename_file = open(conn_msg_filename, "w")

    device_info_filename = "{}{}_device_info.txt".format(folder, current_time)
    device_info_filename_file = open(device_info_filename, "w")

    export_description_all = "{}{}_description_all.txt".format(folder, current_time)
    export_description_exc_updown = "{}{}_description_exc_updown.txt".format(folder, current_time)
    export_description_short = "{}{}_description_short.txt".format(folder, current_time)
    export_description_all_file = open(export_description_all, "w")
    export_description_exc_updown_file = open(export_description_exc_updown, "w")
    export_description_short_file = open(export_description_short, "w")

    for device in devices:
        if device.connection_status:
            exp_devinfo(device, device_info_filename_file)          # export device info: show, status, etc

            export_description_all_file.write("-" * 80 + "\n")
            export_description_all_file.write("{} : {}\n\n".format(device.hostname, device.ip_address))
            for i in device.description_all:
                export_description_all_file.write(i + "\n")

            export_description_exc_updown_file.write("-" * 80 + "\n")
            export_description_exc_updown_file.write("{} : {}\n\n".format(device.hostname, device.ip_address))
            for i in device.description_exc_updown:
                export_description_exc_updown_file.write(i + "\n")

            export_description_short_file.write("-" * 80 + "\n")
            export_description_short_file.write("{} : {}\n\n".format(device.hostname, device.ip_address))
            for i in device.description_short:
                export_description_short_file.write(i + "\n")

        else:
            failed_connection_count += 1
            conn_msg_filename_file.write("{} {}\n\n".format(current_date, current_time))
            conn_msg_filename_file.write("-"*80 + "\n")
            conn_msg_filename_file.write("{} : {}\n\n".format(device.hostname, device.ip_address))
            conn_msg_filename_file.write("{}\n".format(device.connection_error_msg))

    conn_msg_filename_file.close()
    device_info_filename_file.close()
    export_description_all_file.close()
    export_description_exc_updown_file.close()
    export_description_short_file.close()

    return failed_connection_count


#######################################################################################
# ------------------------------ additional def --------------------------------------#
#######################################################################################


def show_commands(device):

    while True:
        try:
            device.show_platform()
            if len(device.show_platform_log) == 0:
                device.show_errors["show_platform"] += 1
                print("{0:20}{1:25}{2:20}".format(device.hostname, device.ip_address, "ERROR show_platform"))
            else:
                break
        except Exception as err_msg:
            print("{0:20}{1:25}{2:20} msg={3}".format(device.hostname, device.ip_address,
                                                      "EXCEPT ERROR show_platform", err_msg))
            device.show_errors["show_platform"] += 1

    while True:
        try:
            device.show_inf_summary()
            if len(device.show_inf_summary_log) == 0:
                device.show_errors["show_inf_summary"] += 1
                print("{0:20}{1:25}{2:20}".format(device.hostname, device.ip_address, "ERROR show_inf_summary"))
            else:
                break
        except Exception as err_msg:
            print("{0:20}{1:25}{2:20} msg={3}".format(device.hostname, device.ip_address,
                                                      "EXCEPT ERROR show_inf_summary", err_msg))
            device.show_errors["show_inf_summary"] += 1

    while True:
        try:
            device.show_inf_description()
            if len(device.show_inf_description_log) == 0:
                device.show_errors["show_inf_description"] += 1
                print("{0:20}{1:25}{2:20}".format(device.hostname, device.ip_address, "ERROR show_inf_description"))
            else:
                break
        except Exception as err_msg:
            print("{0:20}{1:25}{2:20} msg={3}".format(device.hostname, device.ip_address,
                                                      "EXCEPT ERROR show_inf_description", err_msg))
            device.show_errors["show_inf_description"] += 1


def export_excel(devices, current_time, folder):

    filename = "{}{}_masg_ports.xlsx".format(folder, current_time)
    wb = Workbook()
    sheet = wb.active
    sheet.append(["MASG ASR9010",
                  "0/FT0/SP", "0/FT1/SP",
                  "0/PS0/M0/SP", "0/PS0/M1/SP", "0/PS0/M2/SP", "0/PS0/M3/SP",
                  "0/PS1/M0/SP", "0/PS1/M1/SP", "0/PS1/M2/SP", "0/PS1/M3/SP",
                  "0/0/CPU0", "0/0/0", "0/0/1",
                  "0/1/CPU0", "0/1/0", "0/1/1",
                  "0/2/CPU0", "0/2/0", "0/2/1",
                  "0/3/CPU0", "0/3/0", "0/3/1",
                  "0/4/CPU0", "0/4/0", "0/4/1",
                  "0/5/CPU0", "0/5/0", "0/5/1",
                  "0/6/CPU0", "0/6/0", "0/6/1",
                  "0/7/CPU0", "0/7/0", "0/7/1",
                  "10G Free", "UPLINK", "LOCAL",
                  "10G total", "up", "down", "a-down", "10G total dscr"])
    for device in devices:
        if device.connection_status:
            sheet.append([device.hostname,
                          device.platform["0/FT0/SP"], device.platform["0/FT1/SP"],
                          device.platform["0/PS0/M0/SP"], device.platform["0/PS0/M1/SP"],
                          device.platform["0/PS0/M2/SP"], device.platform["0/PS0/M3/SP"],
                          device.platform["0/PS1/M0/SP"], device.platform["0/PS1/M1/SP"],
                          device.platform["0/PS1/M2/SP"], device.platform["0/PS1/M3/SP"],
                          device.platform["0/0/CPU0"], device.platform["0/0/0"], device.platform["0/0/1"],
                          device.platform["0/1/CPU0"], device.platform["0/1/0"], device.platform["0/1/1"],
                          device.platform["0/2/CPU0"], device.platform["0/2/0"], device.platform["0/2/1"],
                          device.platform["0/3/CPU0"], device.platform["0/3/0"], device.platform["0/3/1"],
                          device.platform["0/4/CPU0"], device.platform["0/4/0"], device.platform["0/4/1"],
                          device.platform["0/5/CPU0"], device.platform["0/5/0"], device.platform["0/5/1"],
                          device.platform["0/6/CPU0"], device.platform["0/6/0"], device.platform["0/6/1"],
                          device.platform["0/7/CPU0"], device.platform["0/7/0"], device.platform["0/7/1"],
                          device.tengig["down_description"], device.uplink, device.local,
                          device.tengig["total"], device.tengig["up"], device.tengig["down"],
                          device.tengig["admin down"],
                          device.tengig["total_description"]
                          ])
        else:
            sheet.append([device.hostname, "unavailable"])

    wb.save(filename)


def parse_show_platform(device):
    ft = 0
    pw = 0
    for line in device.show_platform_log.splitlines():
        line_list = line.split()
        if len(line_list) > 0:
            if line_list[0] == r"0/0/CPU0" or line_list[0] == r"0/0/0" or line_list[0] == r"0/0/1":
                device.platform[line_list[0]] = line_list[1]
            elif line_list[0] == r"0/1/CPU0" or line_list[0] == r"0/1/0" or line_list[0] == r"0/1/1":
                device.platform[line_list[0]] = line_list[1]
            elif line_list[0] == r"0/2/CPU0" or line_list[0] == r"0/2/0" or line_list[0] == r"0/2/1":
                device.platform[line_list[0]] = line_list[1]
            elif line_list[0] == r"0/3/CPU0" or line_list[0] == r"0/3/0" or line_list[0] == r"0/3/1":
                device.platform[line_list[0]] = line_list[1]
            elif line_list[0] == r"0/4/CPU0" or line_list[0] == r"0/4/0" or line_list[0] == r"0/4/1":
                device.platform[line_list[0]] = line_list[1]
            elif line_list[0] == r"0/5/CPU0" or line_list[0] == r"0/5/0" or line_list[0] == r"0/5/1":
                device.platform[line_list[0]] = line_list[1]
            elif line_list[0] == r"0/6/CPU0" or line_list[0] == r"0/6/0" or line_list[0] == r"0/6/1":
                device.platform[line_list[0]] = line_list[1]
            elif line_list[0] == r"0/7/CPU0" or line_list[0] == r"0/7/0" or line_list[0] == r"0/7/1":
                device.platform[line_list[0]] = line_list[1]
            elif line_list[0] == r"0/FT0/SP" or line_list[0] == r"0/FT1/SP":
                device.platform[line_list[0]] = line_list[1]
            elif r"0/PS0" in line_list[0] or r"0/PS1" in line_list[0]:
                device.platform[line_list[0]] = line_list[1]


def parse_show_inf_summary(device):
    for line in device.show_inf_summary_log.splitlines():
        line_list = line.split()
        if len(line_list) > 0:
            if line_list[0] == "IFT_TENGETHERNET":
                device.tengig["total"] = int(line_list[1])          # Total
                device.tengig["up"] = int(line_list[2])             # UP
                device.tengig["down"] = int(line_list[3])           # Down
                device.tengig["admin down"] = int(line_list[4])     # Admin Down


def parse_show_inf_description(device):
    for line in device.show_inf_description_log.splitlines():
        line_list = line.split()
        if len(line_list) > 0:
            if r"Te0/" in line_list[0] and r"." not in line_list[0]:  # Te0/0/1/0 up up #UPLINK#
                device.tengig["total_description"] += 1
                if len(line_list) == 3 and "down" in line_list[1]:
                    device.tengig["down_description"] += 1


def count_uplink(device):
    for line in device.show_inf_description_log.splitlines():
        line_list = line.split()
        if len(line_list) >= 4:
            if r"Te0/" in line_list[0] and r"." not in line_list[0]:
                if "BBONE" in line_list[3] or "BBUPLINK" in line_list[3]:
                    device.uplink += 1
                elif "LOCAL" in line_list[3]:
                    device.local += 1


def count_inf_description(device):
    for line in device.show_inf_description_log.splitlines():
        line_list = line.split()
        if len(line_list) >= 4 and r"." not in line_list[0]:
            if r"Te0/" in line_list[0]:
                device.description_all.append(line_list[3])
                if "BBONE" not in line_list[3] and "DOWNLINK" not in line_list[3] \
                        and "BBUPLINK" not in line_list[3] and "LOCAL" not in line_list[3]:
                    device.description_exc_updown.append(line_list[3])
                if len(line_list[3]) < 25:
                    device.description_short.append(line_list[3])
