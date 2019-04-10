{%- from "metalk8s/map.jinja" import etcd with context %}

include:
  - metalk8s.req.certs

Create apiserver etcd client private key:
  x509.private_key_managed:
    - name: /etc/kubernetes/pki/apiserver-etcd-client.key
    - bits: 2048
    - verbose: False
    - user: root
    - group: root
    - mode: 600
    - makedirs: True
    - dir_mode: 755
    - require:
      - pkg: Install m2crypto

Generate apiserver etcd client certificate:
  x509.certificate_managed:
    - name: /etc/kubernetes/pki/apiserver-etcd-client.crt
    - public_key: /etc/kubernetes/pki/apiserver-etcd-client.key
    - ca_server: {{ pillar['metalk8s']['ca']['minion'] }}
    - signing_policy: {{ etcd.cert.apiserver_client_signing_policy }}
    - CN: kube-apiserver-etcd-client
    - O: "system:masters"
    - user: root
    - group: root
    - mode: 644
    - makedirs: True
    - dir_mode: 755
    - require:
      - x509: Create apiserver etcd client private key
