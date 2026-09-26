import urllib.parse
import ipaddress
import socket

# Allowed local hosts & default whitelist
DEFAULT_ALLOWED_DOMAINS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "192.168.",
    "qa-platform.io",
    "example.com"
]

# Blocked cloud metadata & dangerous IP networks
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / Cloud Metadata (AWS/GCP/Azure)
    ipaddress.ip_network("100.64.0.0/10"),   # Carrier-grade NAT
    ipaddress.ip_network("224.0.0.0/4"),     # Multicast
    ipaddress.ip_network("240.0.0.0/4"),     # Reserved
    ipaddress.ip_network("0.0.0.0/8"),       # Current network
]

BLOCKED_METADATA_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.gcp.internal",
    "instance-data",
    "169.254.169.253",
    "fd00:ec2::254"
}

ALLOWED_SCHEMES = {"http", "https"}

def is_safe_target_url(url_string, allowed_domains=None, allow_external=False, resolve_dns=False):
    """
    Validates a target web URL to prevent SSRF (Server-Side Request Forgery),
    cloud metadata exfiltration, DNS rebinding, and unauthorized internal network probes.
    """
    if not url_string or not isinstance(url_string, str):
        return False, "Target URL must be a non-empty string"

    url_clean = url_string.strip()
    if not url_clean:
        return False, "Target URL cannot be empty"

    try:
        parsed = urllib.parse.urlparse(url_clean)
    except Exception as e:
        return False, f"Malformed URL: {e}"

    # 1. Scheme Check: Only HTTP and HTTPS permitted
    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        return False, f"Forbidden protocol '{parsed.scheme}'. Only http:// and https:// URLs are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "Missing valid hostname in target URL"

    hostname_lower = hostname.lower()

    # 2. Port Validation (if specified)
    try:
        if parsed.port is not None:
            if not (1 <= parsed.port <= 65535):
                return False, f"Invalid port number: {parsed.port}"
    except (ValueError, Exception) as pe:
        return False, f"Invalid port number in target URL: {pe}"

    # 3. Block Cloud Metadata Hostnames
    if hostname_lower in BLOCKED_METADATA_HOSTS or "metadata.google.internal" in hostname_lower or "169.254.169.254" in hostname_lower:
        return False, "Access to cloud metadata endpoints is strictly blocked for security."

    # 4. Check Raw IP Address Restrictions
    try:
        ip_obj = ipaddress.ip_address(hostname_lower)
        for blocked_net in BLOCKED_IP_NETWORKS:
            if ip_obj in blocked_net:
                return False, f"Access to IP address {hostname_lower} is blocked (SSRF Protection)."
        if ip_obj.is_link_local:
            return False, f"Link-local address {hostname_lower} is blocked for security."
    except ValueError:
        # Hostname is a domain name, not a raw IP
        pass

    # 5. Domain Whitelist Check
    if not allow_external:
        active_whitelist = allowed_domains or DEFAULT_ALLOWED_DOMAINS
        matches_whitelist = any(
            hostname_lower == d.lower() or
            hostname_lower.endswith("." + d.lower()) or
            hostname_lower.startswith(d.lower())
            for d in active_whitelist
        )
        if not matches_whitelist:
            return False, f"Hostname '{hostname}' is not in the allowed domain whitelist. Please use localhost, 127.0.0.1, or configure allowed domains in Settings."

    # 6. Optional DNS resolution check to prevent DNS rebinding
    if resolve_dns and not (hostname_lower in ("localhost", "127.0.0.1", "0.0.0.0")):
        try:
            addr_info = socket.getaddrinfo(hostname_lower, None)
            for item in addr_info:
                resolved_ip_str = item[4][0]
                resolved_ip = ipaddress.ip_address(resolved_ip_str)
                for blocked_net in BLOCKED_IP_NETWORKS:
                    if resolved_ip in blocked_net:
                        return False, f"Domain {hostname_lower} resolved to blocked IP {resolved_ip_str} (SSRF Protection)."
                if resolved_ip.is_link_local:
                    return False, f"Domain {hostname_lower} resolved to link-local IP {resolved_ip_str}."
        except socket.gaierror:
            pass  # If resolution fails in offline environment, rely on domain whitelist

    return True, "URL is valid and safe"

def validate_navigation_target(target_path_or_url, base_url="http://127.0.0.1:5000", allowed_domains=None, allow_external=False):
    """
    Validates any navigation action target (full URL or relative path)
    before handing it over to Selenium WebDriver.
    """
    if not target_path_or_url or not isinstance(target_path_or_url, str):
        return False, "Navigation target must be a non-empty string", None

    target_clean = target_path_or_url.strip()

    # Handle relative paths safely
    if target_clean.startswith("/"):
        full_url = urllib.parse.urljoin(base_url, target_clean)
    elif target_clean.startswith("http://") or target_clean.startswith("https://"):
        full_url = target_clean
    else:
        full_url = f"{base_url.rstrip('/')}/{target_clean}"

    is_valid, msg = is_safe_target_url(full_url, allowed_domains=allowed_domains, allow_external=allow_external)
    return is_valid, msg, full_url
