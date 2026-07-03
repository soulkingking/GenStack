import socket
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.core.version import APP_VERSION


@dataclass(frozen=True)
class NacosRegistration:
    """记录已注册实例的信息，注销时必须与注册参数完全一致。"""

    client: Any
    service_name: str
    group_name: str
    ip: str
    port: int


def _probe_target(server_addr: str) -> tuple[str, int]:
    """从集群地址列表取第一个节点作为本机网卡探测目标。"""

    first_node = server_addr.split(",")[0].strip()
    host, _, port = first_node.partition(":")
    return host, int(port) if port else 8848


def resolve_instance_ip(settings: Settings) -> str:
    """返回注册到 Nacos 的实例 IP，未显式配置时自动探测。"""

    if settings.nacos_instance_ip:
        return settings.nacos_instance_ip
    host, port = _probe_target(settings.nacos_server_addr)
    # UDP connect 不真正发包，仅让内核选出能到达 Nacos 的本地网卡地址。
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect((host, port))
        return probe.getsockname()[0]


async def register(settings: Settings) -> NacosRegistration:
    """连接 Nacos 并注册当前实例，返回供注销使用的注册信息。"""

    # SDK 及其 gRPC 依赖较重，仅在启用 Nacos 时才导入。
    from v2.nacos import ClientConfigBuilder, NacosNamingService, RegisterInstanceParam

    builder = (
        ClientConfigBuilder()
        .server_address(settings.nacos_server_addr)
        .namespace_id(settings.nacos_namespace)
    )
    if settings.nacos_username:
        builder = builder.username(settings.nacos_username).password(settings.nacos_password)

    client = await NacosNamingService.create_naming_service(builder.build())
    instance_ip = resolve_instance_ip(settings)
    try:
        await client.register_instance(
            request=RegisterInstanceParam(
                service_name=settings.nacos_service_name,
                group_name=settings.nacos_group,
                ip=instance_ip,
                port=settings.nacos_instance_port,
                metadata={"version": APP_VERSION},
                # 临时实例依靠 gRPC 长连接自动保活，连接断开后由 Nacos 自动摘除。
                ephemeral=True,
            )
        )
    except Exception:
        await client.shutdown()
        raise
    return NacosRegistration(
        client=client,
        service_name=settings.nacos_service_name,
        group_name=settings.nacos_group,
        ip=instance_ip,
        port=settings.nacos_instance_port,
    )


async def deregister(registration: NacosRegistration) -> None:
    """注销实例并关闭客户端连接。"""

    from v2.nacos import DeregisterInstanceParam

    try:
        await registration.client.deregister_instance(
            request=DeregisterInstanceParam(
                service_name=registration.service_name,
                group_name=registration.group_name,
                ip=registration.ip,
                port=registration.port,
                ephemeral=True,
            )
        )
    finally:
        await registration.client.shutdown()
