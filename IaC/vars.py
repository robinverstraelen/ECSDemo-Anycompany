# The region and account in which you want to deploy

region = 'eu-central-1'
account_id = '322734229598'

# Set the VPC CIDR
cidr = '10.3.0.0/16'

# Do you have a domain name hosted in route 53?
customdomain = True
# If yes, set the hosted zone id and zone name (domain name)
hosted_zone_id = 'Z02295919CBOEA0AXH21'
zone_name = 'webshopdemo.xyz'

# Do you have a SSL certificate stored in ACM?
sslcert = True
# If yes, set the ARN
sslcert_arn = 'arn:aws:acm:eu-central-1:322734229598:certificate/8caaedcd-a2cf-48ea-bea8-0d29b4112a9d'

