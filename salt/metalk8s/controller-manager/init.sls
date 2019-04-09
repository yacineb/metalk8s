#
# State for controller-manager
#
# All this state deploy controller-manager node
#
# Available states
# ================
#
# * installed     -> deploy controller-manager manifest
# * kubeconfig    -> create controller-manager kubeconfig file
#
include:
  - .installed
