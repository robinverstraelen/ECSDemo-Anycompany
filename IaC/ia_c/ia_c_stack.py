from aws_cdk import (
    core, 
    aws_ec2 as ec2, 
    aws_elasticloadbalancingv2 as elb, 
    aws_route53 as r53, 
    aws_route53_targets as alias, 
    aws_rds as rds, 
    aws_secretsmanager as sm,
    aws_certificatemanager as acm,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_ecr_assets as ecra
)
import sys
sys.path.insert(1, '../')
import vars

class IaCStack(core.Stack):
        
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # The code that defines your stack goes here
        
        # Create a VPC
        myvpc = ec2.Vpc(self, "CDKVPC",
            cidr=vars.cidr
        )
        
        # SG for ELB creation
        websitefrontendSG = ec2.SecurityGroup(self, 'websitefrontendSG', 
            vpc=myvpc,
            security_group_name='websitefrontendSG'
        )
        websitefrontendSG.add_ingress_rule(
            peer = ec2.Peer.ipv4('0.0.0.0/0'),
            connection = ec2.Port.tcp(80)
        )
        websitefrontendSG.add_ingress_rule(
            peer = ec2.Peer.ipv4('0.0.0.0/0'),
            connection = ec2.Port.tcp(443)
        )
        
        # Create ALB in VPC
        alb = elb.ApplicationLoadBalancer(self, 'websitefrontend-public',
            vpc=myvpc,
            load_balancer_name='websitefrontend-public',
            security_group=websitefrontendSG,
            internet_facing=True
        )
        
        # Add target group to ALB
        catalogtargetgroup = elb.ApplicationTargetGroup(self, 'CatalogTargetGroup',
            port = 80,
            vpc = myvpc,
            target_type = elb.TargetType.IP
        )
        
        # Add http listener to ALB
        alblistenerhttp = elb.ApplicationListener(self, 'alblistenerhttp',
            load_balancer = alb,
            default_target_groups = [catalogtargetgroup],
            port = 80
        )
        
        if vars.sslcert:
            # OPTIONAL - Redirect HTTP to HTTPS
            elb.ApplicationListenerRule(self, 'httpredirectionrule',
                priority = 1,
                host_header = vars.zone_name,
                listener = alblistenerhttp,
                redirect_response = elb.RedirectResponse(
                    status_code = 'HTTP_301',
                    port = '443',
                    protocol = 'HTTPS'
                )
            )
            # OPTIONAL - Add https listener to ALB & attach certificate
            alblistenerhttps = elb.ApplicationListener(self, 'alblistenerhttps',
                load_balancer = alb,
                default_target_groups = [catalogtargetgroup],
                port = 443,
                certificate_arns = [vars.sslcert_arn]
            )
        
        if vars.customdomain:
            # OPTIONAL - Update DNS with ALB
            webshopxyz_zone = r53.HostedZone.from_hosted_zone_attributes(self, id = 'customdomain',
                hosted_zone_id = vars.hosted_zone_id,
                zone_name = vars.zone_name
            )
            webshop_root_record = r53.ARecord(self, 'ALBAliasRecord',
                zone=webshopxyz_zone, 
                target=r53.RecordTarget.from_alias(alias.LoadBalancerTarget(alb))
            )
        
        # SG for ECS creation
        ECSSG = ec2.SecurityGroup(self, 'ECSSecurityGroup', 
            vpc=myvpc, 
            security_group_name='ECS'
        )
        ECSSG.add_ingress_rule(peer = websitefrontendSG, connection = ec2.Port.tcp(80))
        
        # SG for MySQL creation
        MySQLSG = ec2.SecurityGroup(self, 'DBSecurityGroup', 
            vpc=myvpc, 
            security_group_name='DB'
        )
        MySQLSG.add_ingress_rule(peer = ECSSG, connection = ec2.Port.tcp(3306))
        
        # Create DB subnet group
        subnetlist = []
        for subnet in myvpc.private_subnets:
            subnetlist.append(subnet.subnet_id)
        subnetgr = rds.CfnDBSubnetGroup(self, 'democlustersubnetgroup', db_subnet_group_name = 'democlustersubnetgroup', db_subnet_group_description = 'DemoCluster', subnet_ids = subnetlist)
        
        # Create secret db passwd
        secret = sm.SecretStringGenerator(
            exclude_characters = "\"'@/\\", 
            secret_string_template = '{"username": "admin"}',
            generate_string_key = 'password',
            password_length = 40
        )
        dbpass = sm.Secret(self, 'democlusterpass',
            secret_name = 'democlusterpass',
            generate_secret_string = secret
        )
        
        # Create Aurora serverless MySQL instance
        dbcluster = rds.CfnDBCluster(self, 'DemoCluster', 
            engine = 'aurora', 
            engine_mode = 'serverless',
            engine_version = '5.6',
            db_cluster_identifier = 'DemoCluster',
            master_username = dbpass.secret_value_from_json('username').to_string(),
            master_user_password = dbpass.secret_value_from_json('password').to_string(),
            storage_encrypted = True,
            port = 3306,
            vpc_security_group_ids = [MySQLSG.security_group_id],
            scaling_configuration = rds.CfnDBCluster.ScalingConfigurationProperty(auto_pause = True, max_capacity = 4, min_capacity = 1, seconds_until_auto_pause = 300),
            db_subnet_group_name = subnetgr.db_subnet_group_name
        )
        dbcluster.add_override('DependsOn', 'democlustersubnetgroup')

        # Attach database to secret
        attach = sm.CfnSecretTargetAttachment(self, 'RDSAttachment',
            secret_id = dbpass.secret_arn,
            target_id = dbcluster.ref,
            target_type = 'AWS::RDS::DBCluster'
        )
        
        # Upload image into ECR repo
        ecrdemoimage = ecra.DockerImageAsset(self, 'ecrdemoimage',
            directory = '../',
            repository_name = 'demorepo',
            exclude = ['cdk.out']
        )
        
        # Create ECS fargate cluster
        ecscluster = ecs.Cluster(self, "ecsCluster",
            vpc=myvpc
        )
        
        # Create task role for productsCatalogTask
        getsecretpolicystatement = iam.PolicyStatement(actions=["secretsmanager:GetResourcePolicy","secretsmanager:GetSecretValue","secretsmanager:DescribeSecret","secretsmanager:ListSecretVersionIds"], resources=[dbpass.secret_arn], effect=iam.Effect.ALLOW)
        getsecretpolicydocument = iam.PolicyDocument(statements = [getsecretpolicystatement])
        taskrole = iam.Role(self, 'TaskRole',
            assumed_by = iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
            role_name = 'TaskRoleforproductsCatalogTask',
            inline_policies = [getsecretpolicydocument]
        )
        
        # Create task definition
        taskdefinition = ecs.FargateTaskDefinition(self, 'productsCatalogTask',
            cpu = 1024,
            memory_limit_mib = 2048,
            task_role = taskrole
        )
        
        # Add container to task definition
        productscatalogcontainer = taskdefinition.add_container('productscatalogcontainer',
            image = ecs.ContainerImage.from_docker_image_asset(asset=ecrdemoimage),
            environment = {"region": vars.region,"secretname": "democlusterpass"}
        )
        productscatalogcontainer.add_port_mappings(
            ecs.PortMapping(
                container_port = 80,
                host_port = 80
            )
        )
        
        # Create service and associate it with the cluster
        catalogservice = ecs.FargateService(self, 'catalogservice',
            task_definition = taskdefinition,
            assign_public_ip = False,
            security_group = ECSSG,
            vpc_subnets = ec2.SubnetSelection(subnets=myvpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE).subnets),
            cluster = ecscluster,
            desired_count = 2
        )
        
        # Add autoscaling to the service
        scaling = catalogservice.auto_scale_task_count(max_capacity = 20, min_capacity = 1)
        scaling.scale_on_cpu_utilization('ScaleOnCPU',
            target_utilization_percent=70,
            scale_in_cooldown=core.Duration.seconds(amount = 1),
            scale_out_cooldown=core.Duration.seconds(amount = 0)
        )
        
        # Associate the fargate service with load balancer targetgroup
        catalogservice.attach_to_application_target_group(catalogtargetgroup)