#
# State for scheduler
#
# All this state deploy scheduler node
#
# Available states
# ================
#
# * installed     -> deploy scheduler manifest
# * kubeconfig    -> create scheduler kubeconfig file
#
include:
  - .installed
