When `docker compose up`, 3 Management servers start, with two of them already forming a cluster, and one independent server. Run the following command to join the independent server (`172.30.30.13`) to the cluster.

```sh
python -m wire_fabric client join --host 172.30.30.13 --port 8001 --token eyJpcCI6ICIxNzIuMzAuMzAuMTEiLCAicG9ydCI6IDgwMDF9
```

All three of the management servers will start as inavtive, i.e. they re not operational yet. To make them operational, run the below command.

```sh
python -m wire_fabric client activate --host 172.30.30.11 --port 8001
python -m wire_fabric client activate --host 172.30.30.12 --port 8001
python -m wire_fabric client activate --host 172.30.30.13 --port 8001
```

> [!NOTE]
> The above command does not make all of them operational at once. User needs to run the command individually for all the management servers they want to make operational.

Once, the management nodes are operational, a ping command can be fired from one node to another to ensure connectivity.

```sh
docker compose exec fabric_management_2 ping 10.0.0.3
```