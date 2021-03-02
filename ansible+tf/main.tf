variable "hcloud_token" {}
variable "aws_access_key" {}
variable "aws_secret_key" {}
variable "instance_count" {}

variable "devs" {
  type = list
  default = ["app1", "app2", "db"]
}

provider "hcloud" {
  token = var.hcloud_token
}

provider "aws" {
  region = "us-west-1"
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}

resource "random_password" "root_passwd" {
  count = length(var.devs)
  length = 16
  special = true
}

}

data "hcloud_ssh_key" "personal_ssh_key" {
  name = "personal_ssh_key"
  #public_key = file("/home/leo/.ssh/id_rsa_np.pub")
}

resource "hcloud_server" "apps" {
  count = length(var.devs)
  name = var.devs[count.index]
  image = "ubuntu-20.04"
  server_type = "cx11"
  ssh_keys = [data.hcloud_ssh_key.personal_ssh_key.id]
  
  provisioner "remote-exec" {
    inline = ["echo 'root:${random_password.root_passwd[count.index].result}' | chpasswd"]
    
    connection {
      type = "ssh"
      user = "root"
      private_key = file("/home/leo/.ssh/id_rsa_np")
      host = self.ipv4_address
    }
  }
}

data "aws_route53_zone" "gvozdi" {
  name = "gvozdi.xyz."
}

resource "aws_route53_record" "gv" {
  count = length(var.devs)
  depends_on = [hcloud_server.apps]
  zone_id = data.aws_route53_zone.gvozdi.zone_id
  name = "${hcloud_server.apps[count.index].name}.${data.aws_route53_zone.gvozdi.name}"
  type = "A"
  ttl = "300"
  records = [hcloud_server.apps[count.index].ipv4_address]
}

resource "local_file" "output" {
  depends_on = [aws_route53_record.gv]
  content = templatefile("inventory.tmpl",
  {
    dns_name = aws_route53_record.gv.*.name
    ipv4_address = hcloud_server.apps.*.ipv4_address
    root_password = random_password.root_passwd.*.result
  }
  )
  filename = "inventory"
}
