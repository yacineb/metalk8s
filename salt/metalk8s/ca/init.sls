#
# State to manage kubernetes CA server
#
# Available states
# ================
#
# * installed   -> install and advertise as CA server
# * deployed    -> deploy the kubernetes CA certificate
#
include:
  - .installed
