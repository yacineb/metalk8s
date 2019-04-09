#
# Requirements states
#
# 1 directory per requirement.
# Each requirement should contain (at least):
# ===========================================
#
# * installed   -> install the requirement
# * removed     -> remove all the requirement installed by `installed` state
#
include:
  - .certs
  - .preflight
  - .python-kubernetes
