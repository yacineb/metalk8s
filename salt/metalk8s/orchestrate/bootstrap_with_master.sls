Update mine:
  salt.state:
    - tgt: {{ pillar['bootstrap_id'] }}
    - saltenv: {{ saltenv }}
    - sls:
      - metalk8s.mine.ips

Bootstrap CA:
  salt.state:
    - tgt: {{ pillar['bootstrap_id'] }}
    - saltenv: {{ saltenv }}
    - sls:
      - metalk8s.bootstrap.certs.ca

Bootstrap client certs:
  salt.state:
    - tgt: {{ pillar['bootstrap_id'] }}
    - saltenv: {{ saltenv }}
    - sls:
      - metalk8s.bootstrap.certs.clients
    - require:
      - salt: Bootstrap CA

Bootstrap control plane:
  salt.state:
    - tgt: {{ pillar['bootstrap_id'] }}
    - saltenv: {{ saltenv }}
    - sls:
      - metalk8s.bootstrap.kubeconfig
      - metalk8s.bootstrap.control-plane
      - metalk8s.bootstrap.etcd
    - require:
      - salt: Bootstrap client certs

Bootstrap node:
  salt.state:
    - tgt: {{ pillar['bootstrap_id'] }}
    - saltenv: {{ saltenv }}
    - sls:
      - metalk8s.bootstrap.mark_control_plane
      - metalk8s.bootstrap.addons
      - metalk8s.bootstrap.calico
    - require:
      - salt: Bootstrap control plane