from typing import Dict, Set

from .config import Config
from .remnawave import NodeMonitor
from .cloudflare_dns import CloudflareClient, DNSManager
from .utils.logger import get_logger


class MonitoringService:
    def __init__(
        self, config: Config, node_monitor: NodeMonitor, cloudflare_client: CloudflareClient, dns_manager: DNSManager
    ):
        self.config = config
        self.node_monitor = node_monitor
        self.cloudflare_client = cloudflare_client
        self.dns_manager = dns_manager
        self.logger = get_logger(__name__)
        self._zone_id_cache: Dict[str, str] = {}

    async def initialize_and_print_zones(self) -> None:
        self.logger.info("Initializing zones")

        for domain_config in self.config.domains:
            domain = domain_config.get("domain")
            zones = domain_config.get("zones", [])

            zone_id = await self._get_zone_id(domain)
            if not zone_id:
                self.logger.warning(f"Could not find zone_id for domain {domain}")
                continue

            self.logger.info(f"Domain: {domain}, Zone ID: {zone_id}")

            for zone_config in zones:
                zone_name = zone_config.get("name")
                configured_ips = zone_config.get("ips", [])
                ttl = zone_config.get("ttl", 120)
                proxied = zone_config.get("proxied", False)
                full_domain = f"{zone_name}.{domain}"

                self.logger.info(f"  Zone: {full_domain}, TTL: {ttl}, Proxied: {proxied}")
                self.logger.info(f"  Configured IPs: {', '.join(configured_ips)}")

                existing_records = await self.cloudflare_client.get_dns_records(
                    zone_id, name=full_domain, record_type="A"
                )
                if existing_records:
                    existing_ips = [record["content"] for record in existing_records]
                    self.logger.info(f"  Existing DNS records: {', '.join(existing_ips)}")
                else:
                    self.logger.info("  Existing DNS records: None")

        self.logger.info("Initialization complete")

    async def perform_health_check(self) -> None:
        self.logger.info("Starting health check cycle")

        try:
            configured_ips = self._get_all_configured_ips()

            all_nodes = await self.node_monitor.check_all_nodes()
            configured_nodes = [node for node in all_nodes if node.address in configured_ips]

            healthy_nodes = [node for node in configured_nodes if node.is_healthy]
            unhealthy_nodes = [node for node in configured_nodes if not node.is_healthy]
            healthy_addresses = {node.address for node in healthy_nodes}

            self.logger.info(
                f"Configured nodes: {len(configured_nodes)}, Healthy: {len(healthy_nodes)}, Unhealthy: {len(unhealthy_nodes)}"
            )

            if healthy_nodes:
                healthy_addrs = [node.address for node in healthy_nodes]
                self.logger.info(f"Healthy nodes: {', '.join(healthy_addrs)}")

            if unhealthy_nodes:
                unhealthy_info = []
                for node in unhealthy_nodes:
                    reason = []
                    if not node.details.get("is_connected"):
                        reason.append("disconnected")
                    if node.details.get("is_disabled"):
                        reason.append("disabled")
                    if not node.details.get("xray_version"):
                        reason.append("no xray")
                    unhealthy_info.append(f"{node.address} ({', '.join(reason)})")
                self.logger.info(f"Unhealthy nodes: {'; '.join(unhealthy_info)}")

            await self._sync_all_zones(healthy_addresses)

            self.logger.info("Health check cycle completed")

        except Exception as e:
            self.logger.error(f"Error during health check: {e}", exc_info=True)
            raise

    def _get_all_configured_ips(self) -> Set[str]:
        configured_ips = set()
        for domain_config in self.config.domains:
            zones = domain_config.get("zones", [])
            for zone_config in zones:
                ips = zone_config.get("ips", [])
                configured_ips.update(ips)
        return configured_ips

    async def _sync_all_zones(self, healthy_addresses: Set[str]) -> None:
        for domain_config in self.config.domains:
            domain = domain_config.get("domain")
            zones = domain_config.get("zones", [])

            zone_id = await self._get_zone_id(domain)
            if not zone_id:
                self.logger.warning(f"Could not find zone_id for domain {domain}, skipping")
                continue

            for zone_config in zones:
                await self._sync_zone(domain, zone_id, zone_config, healthy_addresses)

    async def _get_zone_id(self, domain: str) -> str:
        if domain in self._zone_id_cache:
            return self._zone_id_cache[domain]

        zone_id = await self.cloudflare_client.get_zone_id_by_domain(domain)
        if zone_id:
            self._zone_id_cache[domain] = zone_id

        return zone_id

    async def _sync_zone(self, domain: str, zone_id: str, zone_config: Dict, healthy_addresses: Set[str]) -> None:
        zone_name = zone_config.get("name")
        configured_ips = zone_config.get("ips", [])
        ttl = zone_config.get("ttl", 120)
        proxied = zone_config.get("proxied", False)

        self.logger.info(f"Syncing zone: {zone_name}.{domain}")

        await self.dns_manager.sync_dns_records(
            zone_id=zone_id,
            zone_name=zone_name,
            domain=domain,
            configured_ips=configured_ips,
            healthy_ips=healthy_addresses,
            ttl=ttl,
            proxied=proxied,
        )
