import configparser as configparser
import json

config = configparser.ConfigParser(interpolation=None)
config.read('packagepoa.cfg')

def raw_config(config_section):
    "try to load the config section"
    if config.has_section(config_section):
        return config[config_section]
    # default
    return config.defaults()

def parse_raw_config(raw_config):
    "parse the raw config to something good"
    poa_config = {}
    boolean_values = []
    int_values = []
    list_values = []

    for value_name in raw_config:
        if value_name in boolean_values:
            poa_config[value_name] = raw_config.getboolean(value_name)
        elif value_name in int_values:
            poa_config[value_name] = raw_config.getint(value_name)
        elif value_name in list_values:
            poa_config[value_name] = json.loads(raw_config.get(value_name))
        else:
            # default
            poa_config[value_name] = raw_config.get(value_name)
    return poa_config
