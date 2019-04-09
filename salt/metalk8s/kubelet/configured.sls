{%- from "metalk8s/map.jinja" import kube_api with context %}
{%- from "metalk8s/map.jinja" import kubernetes with context %}

include:
  - .standalone
  - metalk8s.req.certs
  - metalk8s.ca.deployed

{%- set hostname = salt.network.get_hostname() %}

{%- set apiserver_addr = pillar.get('apiserver_addr') %}
{%- if not apiserver_addr %}
  {%- set apiserver_addr = salt['metalk8s.get_control_plane_ips']()[0] %}
{%- endif %}

Create kubeconfig file for kubelet:
  metalk8s_kubeconfig.managed:
    - name: /etc/kubernetes/kubelet.conf
    - ca_server: {{ pillar['metalk8s']['ca']['minion'] }}
    - signing_policy: {{ kube_api.cert.client_signing_policy }}
    - client_cert_info:
        CN: "system:node:{{ hostname }}"
        O: "system:nodes"
    - apiserver: "https://{{ apiserver_addr }}:6443"
    - cluster: {{ kubernetes.cluster }}
    - require:
      - pkg: Install m2crypto
    - watch_in:
      - service: Ensure kubelet running

Configure kubelet service:
  file.managed:
    - name: /etc/systemd/system/kubelet.service.d/10-metalk8s.conf
    - source: salt://{{ slspath }}/files/service-{{ grains['init'] }}.conf
    - template: jinja
    - user: root
    - group : root
    - mode: 644
    - makedirs: True
    - dir_mode: 755
    - context:
        env_file: "/var/lib/kubelet/kubeadm-flags.env"
        config_file: "/var/lib/kubelet/config.yaml"
    - require:
      - pkg: Install kubelet
      - metalk8s_kubeconfig: Create kubeconf file for kubelet
    - watch_in:
      - service: Ensure kubelet running
