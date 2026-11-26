"""Synchronize Cisco 2911 interface state and the IOS configuration."""

from ipaddress import IPv4Interface
from xml.etree import ElementTree as ET

from engine.emit.services import _set, engine_of


def configure_2911(lab, dev_id: str, interfaces: dict[str, str]) -> None:
    engine = engine_of(lab, dev_id)
    if engine.find("TYPE").get("model") != "2911":
        raise ValueError("The interfaces field currently supports the Cisco 2911")
    ports = {
        f"GigabitEthernet0/{index}": port
        for index, port in enumerate(engine.iter("PORT"))
    }
    config = engine.find("RUNNINGCONFIG")
    for name, address in interfaces.items():
        if name not in ports:
            raise ValueError(f"Unknown Cisco 2911 interface: {name}")
        interface = IPv4Interface(address)
        port = ports[name]
        _set(port, "IP", str(interface.ip))
        _set(port, "SUBNET", str(interface.netmask))
        _set(port, "POWER", "true")
        header = f"interface {name}"
        # Replace the template stanza if it exists. Append before IOS 'end'
        # when the supplied ios_config has no stanza for this interface.
        index = next((i for i, line in enumerate(config) if line.text == header), None)
        if index is None:
            index = next((i for i, line in enumerate(config) if line.text == "end"), len(config))
        else:
            config.remove(config[index])
            while index < len(config) and (config[index].text or "").startswith(" "):
                config.remove(config[index])
        for offset, line in enumerate((
            header,
            f" ip address {interface.ip} {interface.netmask}",
            " duplex auto",
            " speed auto",
            "!",
        )):
            item = ET.Element("LINE")
            item.text = line
            config.insert(index + offset, item)
