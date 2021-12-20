#!/bin/bash

set -euo pipefail

SRC_TOKEN='b1xzGznNWZEsvDQCfxXX'
SRC_GITLAB_URL="localhost:8929"
SRC_GROUP="35"
SRC_PROJECT="34"

DST_TOKEN='BoPekQVSPEwpu6Usmyez'
DST_GITLAB_URL="localhost:8930"

TEMP_EXPORT_PATH="./export.tar.gz"
LOGS_PATH="./logs.txt"

# $1: Group ID
# $2: Output file path
export_group()
{
  local group_id=$1
  local output_file_path=$2

  # Export group
  echo "Exporting group [${group_id}]."
  curl -kfsSL --request POST --header "PRIVATE-TOKEN: ${SRC_TOKEN}" "https://${SRC_GITLAB_URL}/api/v4/groups/${group_id}/export" > ${LOGS_PATH}

  # Retry download until successful
  local exported=0
  while (( exported == 0 )); do
    if ! curl -kfsSL --header "PRIVATE-TOKEN: ${SRC_TOKEN}" "https://${SRC_GITLAB_URL}/api/v4/groups/${group_id}/export/download" > ${output_file_path} 2> ${LOGS_PATH}; then
      echo "Group [${group_id}] export is not ready yet. This will take some time..."
      sleep 5
    else
      echo "Group [${group_id}] successfully exported."
      exported=1
    fi
  done
}

# $1: Input file path
import_group()
{
  local input_file_path=$1

  # Import group
  echo "Importing group."
  curl -kfsSL --request POST --header "PRIVATE-TOKEN: ${DST_TOKEN}" \
     --form "name=imported-group" --form "path=imported-group" \
     --form "file=@${input_file_path}" "https://${DST_GITLAB_URL}/api/v4/groups/import"
}

# $1: Project ID
# $2: Output file path
export_project()
{
  local project_id=$1
  local output_file_path=$2
  
  # Export project
  echo "Exporting project [${project_id}]."
  curl -kfsSL --request POST --header "PRIVATE-TOKEN: ${SRC_TOKEN}" "https://${SRC_GITLAB_URL}/api/v4/projects/${project_id}/export" > ${LOGS_PATH}

  # Wait for project to be exported
  local exported=0
  while (( exported == 0 )); do
    export_status=$(curl -kfsSL --header "PRIVATE-TOKEN: ${SRC_TOKEN}" "https://${SRC_GITLAB_URL}/api/v4/projects/${project_id}/export" | jq -r '.export_status')
    if [[ "${export_status}" != "finished" ]]; then
      echo "Project [${project_id}] export status is ${export_status}..."
      sleep 1
    else
      echo "Project [${project_id}] export status is ready."
      exported=1
    fi
  done

  # Download
  echo "Exporting project [${project_id}]."
  curl -kfsSL --header "PRIVATE-TOKEN: ${SRC_TOKEN}" "https://${SRC_GITLAB_URL}/api/v4/projects/${project_id}/export/download" > ${output_file_path} 2> ${LOGS_PATH}
}

# $1: Input file path
import_project()
{
  local input_file_path=$1
  
  # Import project
  echo "Importing project."
  curl -kfsSL --request POST --header "PRIVATE-TOKEN: ${DST_TOKEN}" \
     --form "path=api-project" --form "file=@${input_file_path}" \
     "https://${DST_GITLAB_URL}/api/v4/projects/import"
}

# --- MAIN ---
command -v curl > /dev/null || (echo "This script requires curl." && exit 1)
command -v jq > /dev/null || (echo "This script requires jq." && exit 1)

# export_group ${SRC_GROUP} ${TEMP_EXPORT_PATH}
# import_group ${TEMP_EXPORT_PATH}

export_project ${SRC_PROJECT} ${TEMP_EXPORT_PATH}
import_project ${TEMP_EXPORT_PATH}