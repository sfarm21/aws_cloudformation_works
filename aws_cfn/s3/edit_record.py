import boto3

def listRecordName(recordset_list):
    result = []
    for recordset in recordset_list:
        if recordset["Type"] == "A":
            result.append(recordset["Name"])
    return result

def editRecord(route53Client, hosted_zone_id, record_name, ip_address, edit_mode):
    result = {}
    if edit_mode == "UPSERT" or edit_mode == "DELETE":
        change_batch = {
            "Changes": [
                {
                    "Action": edit_mode,
                    "ResourceRecordSet": {
                        "Name": record_name,
                        "Type": "A",
                        "TTL": 300,
                        "ResourceRecords": [
                            {"Value": ip_address}
                        ]
                    }
                }
            ]
        }
        result = route53Client.change_resource_record_sets(
            HostedZoneId = hosted_zone_id,
            ChangeBatch = change_batch
        )
    return result

def lambda_handler(event, context):
    instance_id = event["detail"]["EC2InstanceId"]
    region = event["region"]
    metadata_str = event["detail"]["NotificationMetadata"]

    metadata = metadata_str.split(",")
    if len(metadata) != 3:
        print("Format error!: {}".format(metadata_str))
        print("Correct: NODE_NAME,HOSTEDZONE_NAME,EDIT_MODE")
        exit()
    else:
        node_name = metadata[0]
        hostedzone_name = metadata[1]
        edit_mode = metadata[2]

    ec2 = boto3.resource("ec2")
    ec2Instance = ec2.Instance(instance_id)
    route53Client = boto3.client("route53")

    hostedzones_list = route53Client.list_hosted_zones_by_vpc(
        VPCId = ec2Instance.vpc_id,
        VPCRegion = region
    )["HostedZoneSummaries"]

    hostedzone_id = ""
    for hostedzone in hostedzones_list:
        if hostedzone["Name"] == hostedzone_name:
            hostedzone_id = hostedzone["HostedZoneId"]
            break
    if hostedzone_id == "":
        print("Not found target hosted zone: {}".format(hostedzone_name))
        exit()

    response = {}
    # Append process
    if edit_mode == "UPSERT":
        recordset_list = route53Client.list_resource_record_sets(
            HostedZoneId = hostedzone_id
        )["ResourceRecordSets"]
        record_name_list = listRecordName(recordset_list)        
        i = 1
        while True:
            append_record_name = node_name + str(i) + "." + hostedzone_name
            if append_record_name not in record_name_list:
                break
            i = i + 1

        print(
            "hostedzone_id: {}\n"
            "append_record_name: {}\n"
            "private_ip_address: {}"
            .format(
                hostedzone_id,
                append_record_name,
                ec2Instance.private_ip_address
            )
        )

        response = editRecord(
            route53Client,
            hostedzone_id,
            append_record_name,
            ec2Instance.private_ip_address,
            edit_mode
        )
        print(response)

        ec2Instance.create_tags(
            Tags = [
                {
                    "Key": "dns_name",
                    "Value": append_record_name
                }
            ]
        )
    # Delete process
    elif edit_mode == "DELETE":
        delete_record_name = ""
        for tag in ec2Instance.tags:
            if tag["Key"] == "dns_name":
                delete_record_name = tag["Value"]
                break
        if delete_record_name == "":
            print("Not found the record name to be deleted.")
            exit()

        print(
            "hostedzone_id: {}\n"
            "delete_record_name: {}\n"
            "private_ip_address: {}"
            .format(
                hostedzone_id,
                delete_record_name,
                ec2Instance.private_ip_address
            )
        )

        response = editRecord(
            route53Client,
            hostedzone_id,
            delete_record_name,
            ec2Instance.private_ip_address,
            edit_mode
        )
        print(response)
    # Invalid argument
    else:
        print("Mode name error!: {}".format(edit_mode))
        print("Correct: UPSERT or DELETE")
        exit()
