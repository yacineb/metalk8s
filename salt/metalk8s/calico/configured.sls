{%- from "metalk8s/map.jinja" import kube_api with context %}
{%- from "metalk8s/map.jinja" import kubernetes with context %}

include:
  - metalk8s.req.certs

Create kubeconf file for calico:
  metalk8s_kubeconfig.managed:
    - name: /etc/kubernetes/calico.conf
    - ca_server: {{ pillar['metalk8s']['ca']['minion'] }}
    - signing_policy: {{ kube_api.cert.client_signing_policy }}
    - client_cert_info:
        CN: {{ salt['network.get_hostname']() }}
        O: metalk8s:calico-node
    - apiserver: https://{{ kube_api.service_ip }}:443
    - cluster: {{ kubernetes.cluster }}
    - require:
      - pkg: Install m2crypto

Create CNI calico configuration file:
  file.serialize:
    - name: /etc/cni/net.d/10-calico.conflist
    - user: root
    - group: root
    - mode: 644
    - makedirs: True
    - dir_mode: 755
    - formatter: json
    - dataset:
        name: k8s-pod-network
        cniVersion: "0.3.0"
        plugins:
          - type: "calico"
            log_level: "info"
            datastore_type: "kubernetes"
            nodename: {{ salt['network.get_hostname']() }}
            mtu: 1440
            ipam:
              type: "host-local"
              subnet: "usePodCidr"
            policy:
              type: "k8s"
            kubernetes:
              kubeconfig: "/etc/kubernetes/calico.conf"
          - type: "portmap"
            snat: true
            capabilities:
              portMappings: true
    - require:
      - metalk8s_kubeconfig: Create kubeconf file for calico
