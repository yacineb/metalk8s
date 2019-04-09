#
# State for apiserver
#
# All this state deploy apiserver node
#
# Available states
# ================
#
# * installed     -> deploy apiserver manifest
# * kubeconfig    -> create admin kubeconfig file
#
include:
  - .installed
  - .kubeconfig
