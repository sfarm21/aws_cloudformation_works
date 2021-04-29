$in_file="work-main.yml"
$out_file="work-main-template.yml"
$s3_bucket="cfn-workspace-2021****"

aws cloudformation package --template-file ${in_file} --s3-bucket ${s3_bucket} --output-template-file ${out_file}