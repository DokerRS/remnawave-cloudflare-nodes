from typing import List, Set
from .client import CloudflareClient
from ..utils.logger import get_logger


class DNSManager:
    def __init__(self, client: CloudflareClient):
        self.client = client
        self.logger = get_logger(__name__)

    async def sync_dns_records(
        self,
        zone_id: str,
        zone_name: str,
        domain: str,
        configured_ips: List[str],
        healthy_ips: Set[str],
        ttl: int = 120,
        proxied: bool = False,
    ) -> None:
        full_domain = f"{zone_name}.{domain}"

        existing_records = await self.client.get_dns_records(zone_id, name=full_domain, record_type="A")
        existing_ips = {record["content"]: record for record in existing_records}

        configured_set = set(configured_ips)
        healthy_configured_ips = configured_set & healthy_ips

        ips_to_add = configured_set & healthy_ips - set(existing_ips.keys())
        ips_to_remove = set(existing_ips.keys()) - (configured_set & healthy_ips)

        status_parts = [
            f"configured: {len(configured_ips)}",
            f"healthy: {len(healthy_configured_ips)}",
            f"existing: {len(existing_records)}",
        ]

        if ips_to_add:
            self.logger.info(f"  {full_domain}: {', '.join(status_parts)}, adding: {', '.join(ips_to_add)}")
            for ip in ips_to_add:
                try:
                    await self.client.create_dns_record(
                        zone_id=zone_id, name=full_domain, content=ip, record_type="A", ttl=ttl, proxied=proxied
                    )
                    self.logger.info(f"  Added DNS record: {ip}")
                except Exception as e:
                    self.logger.error(f"  Failed to add DNS record {ip}: {e}")

        if ips_to_remove:
            self.logger.info(f"  {full_domain}: {', '.join(status_parts)}, removing: {', '.join(ips_to_remove)}")
            for ip in ips_to_remove:
                try:
                    record = existing_ips[ip]
                    await self.client.delete_dns_record(zone_id, record["id"])
                    self.logger.info(f"  Removed DNS record: {ip}")
                except Exception as e:
                    self.logger.error(f"  Failed to remove DNS record {ip}: {e}")

        if not ips_to_add and not ips_to_remove:
            active_ips = [record["content"] for record in existing_records]
            if active_ips:
                self.logger.info(f"  {full_domain}: {', '.join(status_parts)}, active: {', '.join(active_ips)}")
            else:
                self.logger.info(f"  {full_domain}: {', '.join(status_parts)}, no changes needed")

    async def get_all_zone_records(self, zone_id: str, domain: str) -> List[dict]:
        try:
            records = await self.client.get_dns_records(zone_id, record_type="A")
            zone_records = [r for r in records if r["name"].endswith(domain)]
            return zone_records
        except Exception as e:
            self.logger.error(f"Failed to get zone records: {e}")
            return []
