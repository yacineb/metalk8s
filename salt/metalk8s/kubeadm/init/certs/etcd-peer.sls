{%- from "metalk8s/map.jinja" import etcd with context %}

include:
  - .installed

Create etcd peer private key:
  x509.private_key_managed:
    - name: /etc/kubernetes/pki/etcd/peer.key
    - bits: 2048
    - verbose: False
    - user: root
    - group: root
    - mode: 600
    - makedirs: True
    - dir_mode: 755
    - require:
      - pkg: Install m2crypto

Generate etcd peer certificate:
  x509.certificate_managed:
    - name: /etc/kubernetes/pki/etcd/peer.crt
    - public_key: /etc/kubernetes/pki/etcd/peer.key
    - ca_server: {{ pillar['metalk8s']['ca']['minion'] }}
    - signing_policy: {{ etcd.cert.peer_signing_policy }}
    - CN: "{{ grains['fqdn'] }}"
    - subjectAltName: "DNS:{{ grains['fqdn'] }}, DNS:localhost, IP:{{ grains['metalk8s']['control_plane_ip'] }}, IP:127.0.0.1"
    - user: root
    - group: root
    - mode: 644
    - makedirs: True
    - dir_mode: 755
    - require:
      - x509: Create etcd peer private key
