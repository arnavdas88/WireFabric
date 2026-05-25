# Walkthrough

## Architecture

```
( 172.10.0.0/24 )      ( 172.30.30.0/24 )        ( 172.20.0.0/24 )
     Site A                 Internet                  Site B
                            |      |              
    node_wg_1 --------------'      '---------------- node_wg_2 ---. 
                                                                  |
                                                     node_null_3 -'
```

Run `docker compose up`
Then attach to `node_wg_1`
Then ping `172.20.0.2` and `172.20.0.3`