#!/usr/bin/env python3
from snmplib import Rule, PrinterProperties
import argparse
import sys
import yaml


class SNMPWalker(object):
    """
    Iterates over the given hosts and checks the given rules
    Either returns info about the device or the status of the checked rules
    """
    def __init__(self, host_list, rules_list):
        self.hosts = host_list
        self.rules = Rule.parse_rules(rules_list)

    def get_info(self, show_info, show_supplies, show_trays):
        """
        Prints info about a device
        :param show_info: Whether or not to show general device info
        :type show_info: bool
        :param show_supplies: Whether or not to show supply info
        :type show_supplies: bool
        :param show_trays: Whether or not to show tray info
        :type show_trays: bool
        :return: None
        """
        if not show_info and not show_supplies and not show_trays:
            print("No view options given")
            return
        for host in self.hosts:
            print("-"*30)
            print(host)
            try:
                props = PrinterProperties(host)
            except:
                print("Connection error")
                continue
            if show_info:
                print(props.get_info())
            if show_supplies:
                if show_info:
                    print()
                for s in props.get_supplies():
                    print(s)
            if show_trays:
                for s in props.get_trays():
                    print(s)
            print("-" * 30)

    def check_rules(self, sev):
        """
        Matches devices against rules and prints the resulting part status
        :param sev: minimum severity for an error to be shown. 0->OK, 1->Warning, 2->Critical
        :type sev: int
        :return: None
        """
        for host in self.hosts:
            print("-"*30)
            print("Host: %s" % host)
            try:
                props = PrinterProperties(host)
            except:
                print("Connection error")
                continue
            for typ in [props.get_supplies(), props.get_trays()]:
                for s in typ:
                    for r in self.rules:
                        if r.matches(s, host):
                            severity = r.severity
                            ok = s.check(r)
                            if ok:
                                severity = 0
                            if severity >= sev:
                                status = Rule.SEVERITY[0] if ok else Rule.SEVERITY[severity]
                                print("[%s] (%s) => %s" % (status.rjust(4), r.name, s.get_name()))
                            if r.stop:
                                break
            print("-"*30)


def parse_args_and_config():
    """
    Parses command line arguments and the config file
    :return: command line arguments, host list, rule list
    """
    parser = argparse.ArgumentParser(description='Check printers via SNMP.')
    parser.add_argument("--host", "-H", action="append", dest="hosts", metavar="HOST")
    parser.add_argument("--info", "-i", action="store_true")
    parser.add_argument("--supplies", "-s", action="store_true")
    parser.add_argument("--trays", "-t", action="store_true")
    parser.add_argument("--config", "-c")
    parser.add_argument("--applyrules", "-r", action="store_true")
    parser.add_argument("--severity", "-w", type=int, default=0)

    args = vars(parser.parse_args())

    if args["applyrules"] and (args["info"] or args["supplies"] or args["trays"]):
        print("-r and -i|-s|-t| are mutually exclusive")
        sys.exit(2)

    hosts = set()
    rules = []
    if args["config"]:
        with open(args["config"]) as f:
            config = yaml.load(f)
            if "hosts" in config:
                hosts.update(config["hosts"])
            if "rules" in config:
                rules = config["rules"]
    if args["hosts"]:
        hosts.clear()
        hosts.update(args["hosts"])
    if len(hosts) == 0:
        print("Need to specify at least one host")
        sys.exit(1)
    return args, hosts, rules

if __name__ == "__main__":
    a, h, raw_rules = parse_args_and_config()
    walker = SNMPWalker(h, raw_rules)
    if not a["applyrules"]:
        walker.get_info(a["info"], a["supplies"], a["trays"])
    else:
        walker.check_rules(a["severity"])
