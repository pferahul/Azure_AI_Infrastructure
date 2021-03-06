# Running a training job on a single GPU

The goal of this lab is to develop basic understanding of Azure Batch AI service and prepare Azure Batch AI environment for the labs focused on more advanced topics of distributed and parallel training.

Make sure you have activated the conda environment created in Lab00


## Login to your Azure subscription
```
az login
```
If you have multiple subscriptions set the right one with
```
az account set -s <Subscription ID>
```
## Register Batch AI resource providers
Make sure that Batch AI resource providers are registered for you subscription. This is a one-time configuration.
```
az provider register -n Microsoft.BatchAI
az provider register -n Microsoft.Batch
```
## Create a resource group
Batch AI clusters and jobs are Azure resources and must be placed in an Azure resource group
```
az group create --name <Resource group name> --location westus2
az configure --defaults group=<Resource group Name>
az configure --defaults location=westus2
```

## Create a storage account
We will use an Azure file share backed up by  Azure storage to store training data, training scripts, training logs, checkpoints, and the final model.
```
az storage account create --name <Storage Account Name> --sku Standard_LRS
```
### Set environmnent variables
To simplify further commands we can set up environmental variables with the storage account name and the access key
```
az storage account keys list \
    -n <Storage account name> \
    -o table
export AZURE_STORAGE_ACCOUNT=<Storage account name>
export AZURE_STORAGE_ACCESS_KEY=<Storage account access key>
```

## Prepare Azure file share
### Create a file share
```
az storage share create \
    --account-name <Storage account Name>
    --name <File share name>
```

### Create data and scripts directories in the share
```
az storage directory create \
    --share-name  <File share name>
    --name data

az storage directory create \
    --share-name  <File share name>
    --name scripts

az storage directory create \
    --share-name  <File share name>
    --name scripts/lab01
```
### Copy training scripts
```
cd <Repo root>/Azure_AI_Infrastructure/Labs/Lab01-SingleGPU
az storage file upload --share-name <File share name> --source train_eval.py --path scripts/lab01
az storage file upload --share-name <File share name> --source resnet.py --path scripts/lab01
az storage file upload --share-name <File share name> --source feed.py --path scripts/lab01
```

### Copy training data
The training data in the TFRecords format have been uploaded to a public container in Azure storage. Use the following command to copy the files to your file share. The `--dryrun` option allows you to verify the configuration before starting the asynchronous copy operation.

```
az storage file copy start-batch \
  --destination-path data \
  --destination-share <File share name> \
  --source-account-name azaiworkshopst \
  --source-account-key VDMMkPm2iXEQrOqN8nmdYu6qo7S2dysN6//i5u7ml3HGLK4D24pfPJfjcx1ByDssGe1pbqnqGFJHesWsNCOnQg== \
  --source-container tinyimagenet \
  --pattern '*' \
  --dryrun
```

### Verify that files are in the right folders
```
az storage file list --share-name <File share name> --path scripts/lab01 -o table
az storage file list --share-name <File share name> --path data -o table
```

## Prepare a GPU cluster

```
az batchai cluster create \
  --name  <Cluster name> \
  --vm-size STANDARD_NC6 \
  --image UbuntuLTS \
  --min 3 \
  --max 3 \
  --storage-account-name <Storage account name> \
  --afs-name <File share name> \
  --afs-mount-path external \
  --user-name <User name> \
  --password <Password>
```

It is recommended, although not required, to use ssh keys instead of passwords

```
az batchai cluster create \
  --name  <Cluster name> \
  --vm-size STANDARD_NC6 \
  --image UbuntuLTS \
  --min 3 \
  --max 3 \
  --storage-account-name <Storage account name> \
  --afs-name <File share name> \
  --afs-mount-path external \
  --ssh-key ~/.ssh/id_rsa.pub \
  --user-name $USER

```
To generate `ssh` keys you can use an app of your choice including ssh-keygen:
```
ssh-keygen -t rsa
```

Or you can generate ssh keys automatically during cluster creation
```
az batchai cluster create \
  --name  <Cluster name> \
  --vm-size STANDARD_NC6 \
  --image UbuntuLTS \
  --min 3 \
  --max 3 \
  --storage-account-name <Storage account name> \
  --afs-name <File share name> \
  --afs-mount-path external \
  --generate-ssh-keys \
  --user-name $USER
```

### Get cluster status
```
az batchai cluster list -o table
```

### List ssh connection info for the nodes in a cluster
```
az batchai cluster list-nodes -n <Cluster name> -o table
```

### Explore the cluster's node
```
ssh <IP address> -p node
cd /mnt/batch/tasks/shared/LS_root/mounts
```


## Create a training job

Walkthrough the job's python files and JSON template file for the job configuration `job.json'`

### Create job
```
az batchai job create \
  --name <Job name> \
  --cluster-name <Cluster name> \
  --config job.json
```
## Monitor the job
### List the jobs
```
az batchai job list -o table
```
### Show the job's status
```
az batchai job show -n <Job name>
```

### List stdout and stderr output
```
az batchai job file list \
  --name <Job nme> \
  --output-directory-id stdouterr
```

### Stream files from output directories
```
az batchai job file stream \
  -n <Job name> \
  -d stdouterr \
  -f <File to stream>
```
### Use Azure portal
You can also use Azure portal to monitor the job.

### Use Tensorboard
#### Mount a Tensorboard logdir folder
##### On Linux
```
sudo mkdir /mnt/<Mount directory name>
sudo mount -t cifs //<Storage account name>.file.core.windows.net/<Share name> /mnt/<Mount directory name> -o vers=2.1,username=<Storage account name>,password=<Storage account key>,dir_mode=0777,file_mode=0777,serverino
```

Note: You may need to install CIFS utilities on your Linux machine. Azure DLVM and DSVM have these pre-installed:
```
sudo apt-get update
sudo apt-get install cifs-utils
```

##### On Windows
```
net use <Drive letter>: \\<Storage account name>.file.core.windows.net\<Share name> <Storage account key> /user:<Storage account name>
```
#### Start tensorboard
Start `tensorboard` on your development VM using the following information

--logdir : Use the path of the job directory on your mount point
```
Example:  /mnt/<filesharename>/<guid>/<batchai cluster name>/<job directory name>
```
--ip :  Type ``` ifconfig ``` to get the IP address of the workstation
```
tensorboard --logdir=<jobdir on a mount point> --ip=<IP address>
```
Launch Tensorboard in a browser using the following URL format

```
http://<workstation dns name>.<region>.cloudapp.net:6006
```

### Terminate/Delete the job
If you want to terminate or delet the job you can use the following commands
```
az batchai job terminate --name <Job name>
az batchai job delete --name <Job name>
```
