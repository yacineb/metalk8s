{% from "metalk8s/map.jinja" import metalk8s with context %}

include:
  - .installed

Start and enable containerd:
  service.running:
    - name: containerd
    - enable: True
    - require:
      - pkg: Install containerd
    - watch:
      - file: Configure registry IP in containerd conf

Inject pause image:
  # The `containerd` states require the `cri` module, which requires `crictl`
  file.managed:
    - name: /tmp/pause-3.1.tar
    - source: salt://{{ slspath }}/files/pause-3.1.tar
    - unless: >-
        ctr -n k8s.io image ls -q | grep k8s.gcr.io/pause | grep 3\\.1
    - require:
      - service: Start and enable containerd
  cmd.run:
    - name: >-
        ctr -n k8s.io image import \
            --base-name k8s.gcr.io/pause \
            /tmp/pause-3.1.tar
    - unless: >-
        ctr -n k8s.io image ls -q | grep k8s.gcr.io/pause | grep 3\\.1
    - require:
      - file: Inject pause image
