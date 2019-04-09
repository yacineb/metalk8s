{%- from "metalk8s/map.jinja" import kube_api with context %}
{%- from "metalk8s/map.jinja" import kubernetes with context %}

{%- set apiserver_addr = pillar.get('apiserver_addr') %}
{%- if not apiserver_addr %}
  {%- set apiserver_addr = salt['metalk8s.get_control_plane_ips']()[0] %}
{%- endif %}

include:
  - metalk8s.req.certs

Create kubeconfig file for scheduler:
  metalk8s_kubeconfig.managed:
    - name: /etc/kubernetes/scheduler.conf
    - ca_server: {{ pillar['metalk8s']['ca']['minion'] }}
    - signing_policy: {{ kube_api.cert.client_signing_policy }}
    - client_cert_info:
        CN: "system:kube-scheduler"
    - apiserver: "https://{{ apiserver_addr }}:6443"
    - cluster: {{ kubernetes.cluster }}
    - require:
      - pkg: Install m2crypto
