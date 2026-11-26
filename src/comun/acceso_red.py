"""
Quién puede conectarse y en qué direcciones escucha el servicio.

Lee y valida las listas de JOBRUNNER_HOST y JOBRUNNER_ALLOWED_NETWORKS, y
decide si la dirección de un cliente está autorizada. Solo usa el módulo
estándar `ipaddress`.

Está en `comun/` porque no depende del servicio: el futuro panel web también
lo va a necesitar para aplicar la misma lista de redes permitidas.

Se apoya en: ADR-013 (acceso de red).
RF/RNF que cubre: RF-20, RNF-12, RNF-13, RNF-26.
"""

import ipaddress

IPRed = ipaddress.IPv4Network | ipaddress.IPv6Network
IPDir = ipaddress.IPv4Address | ipaddress.IPv6Address

# Direcciones que significan "todas las interfaces".
TODAS_LAS_INTERFACES = ("0.0.0.0", "::")


def _partes(texto: str) -> list[str]:
    return [p.strip() for p in (texto or "").split(",") if p.strip()]


def parse_hosts(texto: str) -> list[str]:
    """
    Convierte "127.0.0.1,192.168.43.10" en una lista de direcciones en las que
    escuchar. Acepta IPv4, IPv6 (con o sin corchetes) y la palabra "localhost".

    Lanza ValueError (con el motivo) si la lista está vacía, si algo no es una
    IP o si es una dirección pública de Internet (RNF-26: no se expone a
    Internet). "0.0.0.0" y "::" se aceptan: la lista de redes permitidas sigue
    decidiendo quién entra.
    """
    hosts = []
    for parte in _partes(texto):
        if parte.lower() == "localhost":
            hosts.append("127.0.0.1")
            continue
        try:
            ip = ipaddress.ip_address(parte.strip("[]"))
        except ValueError:
            raise ValueError(f"'{parte}' no es una dirección IP. Usa una IP, por ejemplo 127.0.0.1 "
                             "o la IP de tu equipo en la red local (ip -4 addr).") from None
        if ip.is_global:
            raise ValueError(f"'{parte}' es una dirección pública de Internet; el servicio solo puede "
                             "escuchar en localhost, la red local o la VPN.")
        hosts.append(str(ip))
    if not hosts:
        raise ValueError("la lista está vacía. Ejemplo: 127.0.0.1")
    return list(dict.fromkeys(hosts))          # sin repetidos, en el mismo orden


def parse_redes(texto: str) -> list[IPRed]:
    """
    Convierte "127.0.0.1,192.168.43.0/24,10.8.0.0/24" en redes. Una IP sola
    equivale a /32 (o /128 en IPv6).

    Lanza ValueError si algo no es una red válida o si la red incluye
    direcciones públicas de Internet (por ejemplo 0.0.0.0/0), porque RNF-13
    limita el acceso a localhost, redes privadas o la VPN.
    """
    redes = []
    for parte in _partes(texto):
        try:
            red = ipaddress.ip_network(parte, strict=False)
        except ValueError:
            raise ValueError(f"'{parte}' no es una IP ni una red válida. Ejemplos: 127.0.0.1, "
                             "192.168.43.0/24, 10.8.0.2/32.") from None
        if red.prefixlen == 0 or red.is_global:
            raise ValueError(f"'{parte}' incluye direcciones públicas de Internet; solo se permiten "
                             "localhost, redes privadas (192.168.x.x, 10.x.x.x, 172.16-31.x.x) o la VPN.")
        redes.append(red)
    if not redes:
        raise ValueError("la lista está vacía; con ella nadie podría conectarse. Ejemplo: 127.0.0.1")
    return redes


def normalizar(direccion: str) -> IPDir | None:
    """
    Convierte la dirección que da el socket en un objeto IP. Quita el
    identificador de zona de IPv6 ("fe80::1%eth0") y convierte las IPv4
    vistas desde un socket IPv6 ("::ffff:192.168.1.5") a IPv4.
    Devuelve None si no se puede interpretar.
    """
    try:
        ip = ipaddress.ip_address(str(direccion).split("%", 1)[0])
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        return ip.ipv4_mapped
    return ip


def esta_permitida(direccion: str, redes: list[IPRed]) -> bool:
    """True si la dirección del cliente pertenece a alguna red permitida."""
    ip = normalizar(direccion)
    return ip is not None and any(ip in red for red in redes)


def escucha_en_todas(hosts: list[str]) -> bool:
    """True si alguna dirección de escucha es 'todas las interfaces'."""
    return any(h in TODAS_LAS_INTERFACES for h in hosts)
