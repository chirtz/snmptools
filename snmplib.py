from easysnmp import Session


class SNMPWalkable(object):
    """
    Abstract class for an SNMP property, e.g. Supply info or Tray info
    """
    def __init__(self):
        for at in self.STRUCTURE.values():
            setattr(self, "_%s" % at, None)

    def get_data(self):
        """
        Returns a dictionary representation of the data
        :return: key-value mappings of the class attributes
         :rtype: dict
        """
        r = dict()
        for att in self.__dict__:
            if att.startswith("_"):
                key = att[1:]
                r[key] = self.__dict__[att]
        return r

    def add_data(self, key, entry):
        """
        Adds an attribute to the printer part
        :param key: name of the property
        :type key: str
        :param entry: SNMP get result
        :return: None
        """
        v = int(entry.value) if entry.snmp_type == "INTEGER" else str(entry.value).strip().replace("\x00", "")
        setattr(self, "_%s" % self.STRUCTURE[key], v)

    def get_name(self):
        """
        Returns the name of the printer part
        :return: name of the printer part
        :rtype: str
        """
        return self._name

    def get_type_str(self):
        """
        Returns the type of the printer part
        :return: either "tray" or a supply name
        :rtype: str
        """
        raise NotImplementedError

    def check(self, rule):
        """
        Checks a rule against the device part
        :return: Whether or not the rule is violated
        :rtype: bool
        """
        raise NotImplementedError


class PrinterInfo(object):

    def __init__(self, session):
        self._gather_infos(session)

    def _gather_infos(self, session):
        """
        Requests basic printer info from the SNMP tree
        :param session: snmp session object
        :return: None
        """
        self.serial = session.get("1.3.6.1.2.1.43.5.1.1.17.1").value
        self.name = session.get(("1.3.6.1.2.1.1.5", 0)).value
        self.location = session.get(("1.3.6.1.2.1.1.6", 0)).value
        self.description = session.get(("1.3.6.1.2.1.1.1", 0)).value
        self.contact = PrinterInfo._get_sys_contact(session)
        self.status = PrinterInfo._get_display_text(session).lower()
        self.alerts = PrinterInfo._get_alerts(session)
        self.severity = PrinterInfo._get_max_severity_level(session)

    def get_data(self):
        r = dict()
        r["serial"] = self.serial
        r["name"] = self.name
        r["location"] = self.location
        r["description"] = self.description
        r["contact"] = self.contact
        r["status"] = self.status
        r["alerts"] = self.alerts
        r["severity"] = self.severity
        return r

    @staticmethod
    def _get_max_severity_level(session):
        m = 0
        for item in session.walk("1.3.6.1.2.1.43.18.1.1.2"):
            val = min(int(item.value), 4)
            if val > m:
                m = val
        # map printer's alarm values to ours
        # warning: 4 -> 1
        # critical: 3 -> 2
        # rest: 0
        if m == 4:
            return 1
        if m == 3:
            return 2
        return 0

    @staticmethod
    def _get_sys_contact(session):
        v1 = session.get(("1.3.6.1.2.1.1.4", 0)).value
        if v1 != "":
            return v1
        return session.get("1.3.6.1.2.1.43.5.1.1.4.1").value

    def __str__(self):
        return "Name    : %s\nSerial  : %s\nContact : %s\nLocation: %s\nStatus  : %s\nAlerts  : %s\nDescr   : %s" % (
            self.name,
            self.serial,
            self.contact,
            self.location,
            self.status,
            self.alerts,
            self.description
        )

    @staticmethod
    def _get_alerts(session):
        """
        Fetches current alerts (status) provided by the printer, e.g. "Device online, ready" or "Paper Jam in Tray 3"
        :param session: snmp session object
        :return: status message string
        :rtype: str
        """
        lines = []
        for item in session.walk("1.3.6.1.2.1.43.18.1.1.8"):
            if item.value:
                item = item.value.strip()
                if item not in lines:
                    lines.append(item)
        return ", ".join(lines).replace("Ã¶", "ö")

    @staticmethod
    def _get_display_text(session):
        """
        Fetches the currently displayed text of the printer
        :param session: snmp session object
        :return: text displayed on the printer
        :rtype: str
        """
        lines = []
        for item in session.walk("1.3.6.1.2.1.43.16.5"):
            if item.value:
                item = item.value.strip()
                if item not in lines:
                    lines.append(item)
        return ", ".join(lines)


class Supply(SNMPWalkable):

    STRUCTURE = {
        "1.3.6.1.2.1.43.11.1.1.4": "class",
        "1.3.6.1.2.1.43.11.1.1.5": "type",
        "1.3.6.1.2.1.43.11.1.1.6": "name",
        "1.3.6.1.2.1.43.11.1.1.7": "unit",
        "1.3.6.1.2.1.43.11.1.1.8": "capacity",
        "1.3.6.1.2.1.43.11.1.1.9": "level"
    }
    CLASSES = {1: "other", 3: "consumed", 4: "filled"}
    TYPES = {1: "other", 2: "unknown", 3: "toner", 4: "wasteToner", 5: "ink", 6: "inkCartridge", 7: "inkRibbon",
             8: "wasteInk", 9: "opc", 10: "developer", 11: "fuserOil", 12: "solidWax", 13: "ribbonWax", 14: "wasteWax",
             15: "fuser", 16: "coronaWire", 17: "fuserOilWick", 18: "cleanerUnit", 19: "fuserCleaningPad",
             20: "transferUnit", 21: "tonerCartridge", 22: "fuserOiler", 23: "water", 24: "wasteWater",
             25: "glueWaterAdditive", 26: "wastePaper", 27: "bindingSupply", 28: "bandingSupply", 29: "stitchingWire",
             30: "shrinkWrap", 31: "paperWrap", 32: "staples", 33: "inserts", 34: "covers"}

    UNITS = {1: "other", 2: "unknown", 3: "tenThousandthsOfInches", 4: "micrometers", 7: "impressions", 8: "sheets",
             11: "hours", 12: "thousandthsOfOunces", 13: "tenthsOfGrams", 14: "hundrethsOfFluidOunces",
             15: "tenthsOfMilliliters", 16: "feet", 17: "meters", 18: "items", 19: "percent"}

    def get_data(self):
        r = super().get_data()
        r["str_level"], r["level_percent"] = self._get_level()
        r["str_capacity"] = self._get_capacity_str()
        r["str_unit"] = self._get_unit_str()
        r["str_type"] = self.get_type_str()
        r["str_class"] = self._get_classes_str()
        return r

    def get_type_str(self):
        return Supply.TYPES[self._type]

    def _get_unit_str(self):
        return self.UNITS[self._unit]

    def _get_classes_str(self):
        return self.CLASSES[self._class]

    def _get_level(self):
        if self._level == -3:
            return "OK", 100
        elif self._level == -2:
            return "NA", None
        lvl = (float(self._level) / self._capacity) * 100
        return "{:.1f}%".format(lvl), lvl

    def _get_capacity_str(self):
        if self._capacity > 0:
            return str(self._capacity)
        elif self._capacity == -1:
            return "other / no restrictions"
        else:
            return "unknown"

    def check(self, rule):
        if self._level == -3:
            return True
        if self._level == -2:
            return True
        if not rule.threshold:
            return False
        else:
            return (float(self._level) / self._capacity)*100 >= rule.threshold

    def __str__(self):
        return "[%s]  %s (type: %s, unit: %s, raw: %s, capacity: %s, class: %s)" % (self._get_level()[0].rjust(6, " "),
                                                                                    self._name, self.get_type_str(),
                                                                                    self._get_unit_str(), self._level,
                                                                                    self._get_capacity_str(),
                                                                                    self._get_classes_str())


class Tray(SNMPWalkable):
    STRUCTURE = {
        "1.3.6.1.2.1.43.8.2.1.10": "level",
        "1.3.6.1.2.1.43.8.2.1.11": "status",
        "1.3.6.1.2.1.43.8.2.1.12": "paper",
        "1.3.6.1.2.1.43.8.2.1.18": "name"
    }

    def __init__(self):
        super().__init__()
        self.type = "tray"

    def get_data(self):
        r = super().get_data()
        r["str_level"], r["level_percent"] = self._get_level()
        r["str_status"] = self._get_status_str()
        return r

    def get_type_str(self):
        return "tray"

    def _get_level(self):
        if self._level >= 0:
            return str(self._level), self._level
        if self._level == -1:
            return "OT", None
        elif self._level == -3:
            return "OK", 100
        else:
            return "NA", None

    def _get_status_str(self):
        """
        Return the string representation of the int status
        :rtype: str
        :return: string representation for the int status
        """
        status = self._status
        status_string = ""
        if status >= 64:
            status_string += "Transition to intended state, "
            status -= 64
        if status >= 32:
            status_string += "State is Off-Line, "
            status -= 32
        if status >= 16:
            status_string += "Critical alerts, "
            status -= 16
        if status >= 8:
            status_string += "Non-critical alerts, "
            status -= 8
        if status == 6:
            status_string += "Available and busy, "
        elif status == 5:
            status_string += "Unknown, "
        elif status == 4:
            status_string += "Available and Active, "
        elif status == 3:
            status_string += "Unavailable because broken, "
        elif status == 2:
            status_string += "Available and standby, "
        elif status == 1:
            status_string += "Unavailable and OnRequest, "
        elif status == 0:
            status_string += "Available and Idle, "

        return status_string[:-2]

    def check(self, rule):
        if not rule.status:
            return False
        else:
            return self._status <= rule.status

    def __str__(self):
        return "[%s]  %s (type: %s, paper: %s, status: %d, statustext: %s)" % (self._get_level()[0].rjust(6),
                                                                               self._name, self.get_type_str(),
                                                                               self._paper, self._status,
                                                                               self._get_status_str())


class PrinterProperties(object):
    """
    Wrapper object for all printer properties
    """
    def __init__(self, host_name):
        self.session = Session(hostname=host_name, community="public", version=2)

    def get_supplies(self):
        return self._parse_data(Supply)

    def get_trays(self):
        return self._parse_data(Tray)

    def get_info(self):
        return PrinterInfo(self.session)

    def _parse_data(self, typ):
        """
        Creates a list of printer part objects and fills them with info from the printer
        :param typ:
        :return:
        """
        items = []
        for key in typ.STRUCTURE:
            for idx, entry in enumerate(self.session.walk(key)):
                if idx > len(items)-1:
                    item = typ()
                    items.append(item)
                else:
                    item = items[idx]
                # Do black magic to convert names from the STRUCTURE element to object attributes
                item.add_data(key, entry)
        return items


class Rule(object):
    """
    A rule as defined in the config file
    """
    SEVERITY = {
        0: "OK",
        1: "WARN",
        2: "CRIT"
    }

    def __init__(self, data):
        if "name" not in data:
            raise KeyError("name field missing in rule")
        self.name = data["name"]
        self.match = None if "match" not in data else data["match"]
        self.stop = False if "stop" not in data else data["stop"]
        self.threshold = None if "threshold" not in data else float(data["threshold"])
        self.status = None if "status" not in data else int(data["status"])
        self.severity = 2 if "severity" not in data else int(data["severity"])

    def matches(self, o, h):
        """
        Checks whether or not a rule is applicable to a given printer part and host
        :param o: a printer part object
        :type o: either a Tray object or a Supply object
        :param h: hostname
        :type h str
        :return: True if the rule applies to the given printer part and host
        """
        # if no 'match' section is defined in the rule, it automatically applies
        if not self.match:
            return False
        # if a 'host' section is defined in the rule, check if the name matches the given host name
        if "host" in self.match:
            host = self.match["host"]
            # one single host name provided as string
            if type(host) is str and host != h:
                return False
            # list of host names
            elif type(host) is list:
                if h not in host:
                    return False
        # if a 'name' section is defined in the rule, check if it matches the name of the printer part, e.g.
        # 'Black Toner Cartridge XY'
        if "name" in self.match and self.match["name"] not in o.get_name():
            return False
        # if a 'type' section is defined, check if it matches the printer part type, e.g. 'tonerCartridge'
        if "type" in self.match:
            match_typ = self.match["type"]
            typ = o.get_type_str()
            # if only one type is given (a string)
            if type(match_typ) is str:
                if match_typ not in typ:
                    return False
            # if a type list is given
            elif type(match_typ) is list:
                if not any([t in typ for t in match_typ]):
                    return False
        return True

    @staticmethod
    def parse_rules(rule_list):
        out_list = []
        for r in rule_list:
            out_list.append(Rule(r))
        return out_list
