resource "openstack_compute_instance_v2" "bastion" {
  name        = "${local.prefix}-bastion"
  image_name  = "${var.openstack_image_name}"
  flavor_name = "${var.openstack_flavour_name}"
  key_pair    = "${openstack_compute_keypair_v2.local_ssh_key.name}"

  security_groups = [
    "${openstack_networking_secgroup_v2.nodes.name}",
    "${openstack_networking_secgroup_v2.nodes_internal.name}"
  ]

  network = [
    "${var.openstack_network}",
    "${local.control_plane_network}",
    "${local.workload_plane_network}",
  ]

  # We need the subnets to be created before attempting to reach the DHCP server
  depends_on = [
    "openstack_networking_subnet_v2.control_plane_subnet",
    "openstack_networking_subnet_v2.workload_plane_subnet",
  ]

  connection {
    user        = "centos"
    private_key = "${file("~/.ssh/terraform")}"
  }

  # Obtain IP addresses for both private networks
  provisioner "remote-exec" {
    inline = [
      "sudo chattr +i /etc/resolv.conf",
      "sudo dhclient -r eth1 eth2",  # Release first
      "sudo dhclient eth1 eth2",  # Then request new IPs
    ]
  }

  # Generate Bastion SSH keypair
  provisioner "remote-exec" {
    inline = [
      "ssh-keygen -t rsa -b 4096 -N '' -f /home/centos/.ssh/bastion"
    ]
  }
}

resource "openstack_compute_instance_v2" "bootstrap" {
  name        = "${local.prefix}-bootstrap"
  image_name  = "${var.openstack_image_name}"
  flavor_name = "${var.openstack_flavour_name}"
  key_pair    = "${openstack_compute_keypair_v2.local_ssh_key.name}"

  security_groups = [
    "${openstack_networking_secgroup_v2.nodes.name}",
    "${openstack_networking_secgroup_v2.nodes_internal.name}"
  ]

  network = [
    "${var.openstack_network}",
    "${local.control_plane_network}",
    "${local.workload_plane_network}",
  ]

  # We need the subnets before attempting to reach their DHCP servers
  depends_on = [
    "openstack_networking_subnet_v2.control_plane_subnet",
    "openstack_networking_subnet_v2.workload_plane_subnet",
  ]

  connection {
    user        = "centos"
    private_key = "${file("~/.ssh/terraform")}"
  }

  # Obtain IP addresses for both private networks
  provisioner "remote-exec" {
    inline = [
      "sudo chattr +i /etc/resolv.conf",
      "sudo dhclient -r eth1 eth2",  # Release first
      "sudo dhclient eth1 eth2",  # Then request new IPs
    ]
  }
}

variable "nodes_count" {
  type    = "string"
  default = "1"
}

resource "openstack_compute_instance_v2" "nodes" {
  name        = "${local.prefix}-node-${count.index+1}"
  image_name  = "${var.openstack_image_name}"
  flavor_name = "${var.openstack_flavour_name}"
  key_pair    = "${openstack_compute_keypair_v2.local_ssh_key.name}"

  security_groups = [
    "${openstack_networking_secgroup_v2.nodes.name}",
    "${openstack_networking_secgroup_v2.nodes_internal.name}"
  ]

  network = [
    "${var.openstack_network}",
    "${local.control_plane_network}",
    "${local.workload_plane_network}",
  ]

  # We need the subnets to be created before attempting to reach the DHCP server
  depends_on = [
    "openstack_networking_subnet_v2.control_plane_subnet",
    "openstack_networking_subnet_v2.workload_plane_subnet",
  ]

  connection {
    user        = "centos"
    private_key = "${file("~/.ssh/terraform")}"
  }

  # Obtain IP addresses for both private networks
  provisioner "remote-exec" {
    inline = [
      "sudo chattr +i /etc/resolv.conf",
      "sudo dhclient -r eth1 eth2",  # Release first
      "sudo dhclient eth1 eth2",  # Then request new IPs
    ]
  }

  count = "${var.nodes_count}"
}

locals {
  bastion_ip   = "${openstack_compute_instance_v2.bastion.network.0.fixed_ip_v4}"
  bootstrap_ip = "${openstack_compute_instance_v2.bootstrap.network.0.fixed_ip_v4}"

  # FIXME: this syntax does not work (but will in v0.12)
  # see https://github.com/hashicorp/terraform/issues/17048
  # nodes = ["${openstack_compute_instance_v2.nodes.*.network.0.fixed_ip_v4}"]

  all_instances = "${concat(
    "${list(
      "${openstack_compute_instance_v2.bastion.id}",
      "${openstack_compute_instance_v2.bootstrap.id}"
    )}",
    "${openstack_compute_instance_v2.nodes.*.id}"
  )}"
}



output "ips" {
  value = {
    bastion   = "${local.bastion_ip}"
    bootstrap = "${local.bootstrap_ip}"
  }
}
