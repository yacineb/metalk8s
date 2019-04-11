mine_functions:
  control_plane_ip:
    - mine_function: grains.get
    - metalk8s:control_plane_ip
  workload_plane_ip:
    - mine_function: grains.get
    - metalk8s:workload_plane_ip
  etcd_endpoints:
    - mine_function: metalk8s.get_etcd_endpoint
