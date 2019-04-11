Set control_plane_ip grain:
  grains.present:
    - name: metalk8s:control_plane_ip
    - value: {{ salt['network.ip_addrs'](cidr=salt['pillar.get']('networks:control_plane'))[0] }}

Set workload_plane_ip grain:
  grains.present:
    - name: metalk8s:workload_plane_ip
    - value: {{ salt['network.ip_addrs'](cidr=salt['pillar.get']('networks:workload_plane'))[0] }}
