#
# State to manage etcd CA server
#
# Available states
# ================
#
# * installed   -> install and advertise as CA server
# * deployed    -> deploy the etcd CA certificate
#
include:
  - .installed
