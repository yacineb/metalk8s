#
# State for mark-control-plane phase.
#
# Mark the current node as control-plane node
#
# Available states
# ================
#
# * configured    -> Applies label and taints to the node
#

include:
  - .configured
