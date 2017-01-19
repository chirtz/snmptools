#!/usr/bin/env python3
from snmplib import PrinterProperties, Rule
import sys
import yaml
import couchdb
import datetime
from easysnmp.exceptions import EasySNMPConnectionError 

DB_URL = "https://database-url/"
DB_DATABASE = "printer_stats"
TIMESTAMP_FORMAT = "%d.%m.%Y %H:%M:%S"


# Color definitions used in the mapping below
class COLOR:
    BLACK = "#555555",
    CYAN = "#00bfff",
    LIGHT_CYAN = "#00ffff",
    MAGENTA = "#D028A6",
    LIGHT_MAGENTA = "#ee82ee",
    YELLOW = "#DDD000"
    DEFAULT = "#888787"
    OPTIMIZER = "#cccbcb"
    HEADER_WARNING = "#F6AE24"
    HEADER_CRITICAL = "#DC143C"
    HEADER_WARNING_PRINTER = "#FFD700"
    HEADER_DEFAULT = "#eeeeee"

# Mappings from sub-strings of supply name to color
COLOR_MAPPING = {
    "black": COLOR.BLACK,
    "cyan":  COLOR.CYAN,
    "magenta": COLOR.MAGENTA,
    "yellow": COLOR.YELLOW,
    "schwarz": COLOR.BLACK,
    "gelb": COLOR.YELLOW,
    "cz696a": COLOR.MAGENTA,
    "cz699a": COLOR.LIGHT_MAGENTA,
    "cz698a": COLOR.LIGHT_CYAN,
    "cz695a": COLOR.CYAN,
    "cz706a": COLOR.OPTIMIZER,
    "cz694a": COLOR.BLACK,
    "cz697a": COLOR.YELLOW,
}


def apply_rules(item, host, rule_list):
    """
    Tests each rule for the given supply/tray
    :param item: The supply/tray to check
    :param host: The hostname of the checked device
    :param rule_list: List of rules to check
    :return: The severity of a matched rule or 0 if nothing was matched
    :rtype int
    """
    status = 0
    for r in rule_list:
        if r.matches(item, host):
            ok = item.check(r)
            if not ok and r.severity > status:
                status = r.severity
            if r.stop:
                break
    return status


def get_color(item):
    """
    Returns the color of a supply or a default color (grey)
    :param item: The supply/tray to determine the color for
    :return: hex color string
    :rtype" str
    """
    name = item.get_name().lower()
    for x in COLOR_MAPPING:
        if x in name:
            return COLOR_MAPPING[x]
            break
    return COLOR.DEFAULT


def get_header_color(max_status, status_severity):
    """
    Returns the color of a printer header, depending on the maximal status of the checks
    E.g. if one of the parts of the printers had a warning status and onother part had a critical status,
    return red color for critical
    :param max_status: maximal (worst) error status of all supplies and trays for a device, given by the checks
    :return: hex color string
    :rtype: str
    """
    if max_status == 1:
        return COLOR.HEADER_WARNING
    elif max_status == 2 or max_status == 4:
        return COLOR.HEADER_CRITICAL
    elif status_severity == 1:
        return COLOR.HEADER_WARNING_PRINTER
    else:
        return COLOR.HEADER_DEFAULT


def check_printer(h, rule_list):
    # Get basic device info and info about supplies and trays
    props = PrinterProperties(h)
    info = props.get_info().get_data()
    supplies = props.get_supplies()
    trays = props.get_trays()

    # Initialize the output variables
    out_supplies = []
    out_trays = []
    max_status = 0
    err_parts = []
    name_list = set()

    # check rules on all supplies and trays
    for s in supplies + trays:
        # If a printer part name occurs twice, ignore it (happens e.g. for the latex printers)
        name = s.get_name()
        if name in name_list:
            continue
        name_list.add(name)

        # Get type of the printer part (tray or supply)
        typ = s.get_type_str()

        # Match rules against the printer part
        status = apply_rules(s, h, rule_list)
        # Save maximal error status of all supplies
        if status > max_status:
            max_status = status
        # If a rule matched and errors were found
        if status > 0:
            err_parts.append((s.get_name(), status))
        # Get the color of the printer part, e.g. cyan hex value for a "Cyan Toner Cartridge"
        color = get_color(s)

        # convert printer part object to dictionary
        s = s.get_data()

        # Now we add additional info to the parts, which will be used by the web page
        # Set color of the part
        s["rgb"] = color
        # Set part status
        s["status"] = status
        # Depending on the type, add part to the respective output list
        if typ == "tray":
            out_trays.append(s)
        else:
            out_supplies.append(s)
	
        # Capitalize first letter of each word in printer part name
        s["name"] = " ".join([word[:1].upper() + word[1:] for word in name.split()])

    # Set header color for the printer, depending on the maximum error status
    info["rgb"] = get_header_color(max_status, info["severity"])

    max_status = max(max_status, info["severity"])
    # Set the maximum error status of all printer parts, from both our rules and what the printer itself says
    info["max_status"] = max_status

    # Order printer errors detected by rules by descending severity and only name the first one
    info["err_parts"] = list(reversed(sorted(err_parts, key=lambda elem: elem[1])))
    # number of errors detected by rules
    num_errors = len(info["err_parts"])
    if num_errors == 0:
        info["str_err_parts"] = ""
    elif num_errors == 1:
        info["str_err_parts"] = "Alert for " + info["err_parts"][0][0]
    else:
        info["str_err_parts"] = "Alert for %s and %d more failures(s)" % (info["err_parts"][0][0], num_errors - 1)

    # Create out output dictionary, which will be written to the DB
    data = {
        "info": info,
        "supplies": out_supplies,
        "trays": out_trays
    }
    return data


def check_printers(database, h, rule_list):
    """
    Iterates over all devices, fetches general info and info about supplies and trays, and writes this info to the
    database
    :param database: CouchDB database object
    :param h: host name of the device to be checked
    :param rule_list: list of rules to be matched against
    :return: None
    """
    # Iterate over all devices
    for dev in h:
        if dev not in database:
            dataset = {
                "_id": dev,
                "data": {}
            }
        else:  # if device already exists in DB, update the entry
            dataset = database.get(dev)
        try:
            print("Checking %s" % dev)
            dataset["data"] = check_printer(dev, rule_list)
        # Create a new DB entry if it does not exist, yet

        except EasySNMPConnectionError as e:
            print("Error for %s: %s" % (dev, str(e)))
            dataset["data"]["info"] = {"max_status": 2, "name": dev, "alerts": "Printer offline", "rgb": COLOR.HEADER_CRITICAL}
        finally:
            dataset["data"]["info"]["checked"] = datetime.datetime.now().strftime(TIMESTAMP_FORMAT)
            database.save(dataset)


if __name__ == "__main__":
    # script needs a config file to work
    if len(sys.argv) < 2:
        print("Incorrect number of arguments")
        sys.exit(3)
    config_file = sys.argv[1]

    with open(config_file) as f:
        config = yaml.load(f)
        if "hosts" not in config:
            print("No hosts defined")
            sys.exit(1)
        if "rules" not in config:
            print("No rules defined")
            sys.exit(2)
        rules = Rule.parse_rules(config["rules"])
        if len(sys.argv) == 3:
            hosts = [sys.argv[2]]
        else:
            hosts = config["hosts"]

        db = couchdb.Server(DB_URL)[DB_DATABASE]
        # Run checks and update DB
        check_printers(db, hosts, rules)
