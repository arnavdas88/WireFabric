# Walkthrough

## Architecture

```
( 172.10.0.0/24 )      ( 172.30.30.0/24 )        ( 172.20.0.0/24 )
     Site A                 Internet                  Site B
                            |      |              
    node_wg_1 --------------'      :---------------- node_wg_2 ---. 
                                   |                              |
                                   '---------------- node_wg_3 ---: 
                                                                  |
                                                     node_null_4 -'
```

Run `docker compose up`
Then attach to `node_null_4` and check its IP
Then attach to `node_wg_1` and ping `node_null_4` IP
Then try stopping `node_wg_2` while the ping is running and verify if the connection resumes after a while