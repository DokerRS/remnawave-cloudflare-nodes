from typing import Dict, List
from uuid import UUID


from .client import RemnawaveClient
from ..utils.logger import get_logger


class NodeStatus:
    def __init__(self, name: str, address: str, is_healthy: bool, details: Dict):
        self.name = name
        self.address = address
        self.is_healthy = is_healthy
        self.details = details

    def __repr__(self):
        status = "healthy" if self.is_healthy else "unhealthy"
        return f"NodeStatus(name={self.name}, address={self.address}, status={status})"


class NodeMonitor:
    def __init__(self, client: RemnawaveClient):
        self.client = client
        self.logger = get_logger(__name__)

    async def check_all_nodes(self) -> List[NodeStatus]:
        try:
            nodes = await self.client.get_nodes()
            node_statuses = []

            for node in nodes:
                name = node.name
                address = node.address
                is_healthy = self.client.is_node_healthy(node)

                details = {
                    "uuid": str(node.uuid) if isinstance(node.uuid, UUID) else node.uuid,
                    "is_connected": node.is_connected,
                    "is_disabled": node.is_disabled,
                    "xray_version": node.xray_version,
                    "xray_uptime": node.xray_uptime,
                    "port": node.port,
                    "users_online": node.users_online or 0,
                }

                status = NodeStatus(name, address, is_healthy, details)
                node_statuses.append(status)

                self.logger.debug(f"Node {name} ({address}): {status}")

            healthy_count = sum(1 for s in node_statuses if s.is_healthy)
            self.logger.info(
                f"Checked {len(node_statuses)} nodes: "
                f"{healthy_count} healthy, {len(node_statuses) - healthy_count} unhealthy"
            )

            return node_statuses

        except Exception as e:
            self.logger.error(f"Error checking nodes: {e}")
            raise

    async def get_healthy_nodes(self) -> List[NodeStatus]:
        all_nodes = await self.check_all_nodes()
        return [node for node in all_nodes if node.is_healthy]

    async def get_unhealthy_nodes(self) -> List[NodeStatus]:
        all_nodes = await self.check_all_nodes()
        return [node for node in all_nodes if not node.is_healthy]

    async def get_node_addresses(self, only_healthy: bool = True) -> List[str]:
        if only_healthy:
            nodes = await self.get_healthy_nodes()
        else:
            nodes = await self.check_all_nodes()

        return [node.address for node in nodes if node.address]
